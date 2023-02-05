#!/usr/bin/env python
# coding: utf-8

from copy import deepcopy
import importlib.util
from importlib.metadata import files, version
import json
import mappings
import os
import pandas
import re
import sys
import yaml
import pprint

import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, help="Path to either an xlsx file or a directory of csv files for ingest")
    # parser.add_argument('--api_key', type=str, help="BioPortal API key found in BioPortal personal account settings")
    # parser.add_argument('--email', type=str, help="Contact email to access NCBI clinvar API. Required by Entrez")
    #parser.add_argument('--schema', type=str, help="Schema to use for template; default is mCodePacket")
    parser.add_argument('--manifest', type=str, required = True, help="Path to a manifest file describing the mapping."
                                                                  " See README for more information")
    parser.add_argument('--verbose', '--v', action="store_true", help="Print extra information")
    args = parser.parse_args()
    return args


def process_data(raw_csv_dfs, identifier):
    """Takes a set of raw dataframes with a common identifier and merges into the internal JSON data structure."""
    final_merged = {}
    cols_index = {}
    individuals = []

    for page in raw_csv_dfs.keys():
        print(f"Processing sheet {page}...")
        df = raw_csv_dfs[page].dropna(axis='index', how='all')\
            .dropna(axis='columns', how='all')\
            .applymap(str)\
            .applymap(lambda x: x.strip())\
            .drop_duplicates()  # drop absolutely identical lines

        # Sort by identifier and then tag any dups
        df.set_index(identifier, inplace=True)
        df.sort_index(inplace=True)
        df.reset_index(inplace=True)
        dups = df.duplicated(subset=[identifier], keep='first')

        for col in list(df.columns):
            col = col.strip()
            if col not in cols_index:
                cols_index[col] = [page]
            else:
                cols_index[col].append(page)

        # For all rows with the same identifier, merge all of the occurrences into an array
        rows_to_merge = {}  # this is going to hold all of the rows that will need to be merged...
        df_dict = df.to_dict(orient="index")
        for index in range(0, len(dups)):
            if not dups[index]:  # this is the first occurrence
                rows_to_merge[df_dict[index][identifier]] = [df_dict[index]]
            else:
                rows_to_merge[df_dict[index][identifier]].append(df_dict[index])
        merged_dict = {}  # this is going to be the dict with arrays:
        for i in range(0, len(rows_to_merge)):
            merged_dict[i] = {}
            row_to_merge = rows_to_merge[list(rows_to_merge.keys())[i]]
            row = row_to_merge.pop(0)
            for k in row.keys():
                merged_dict[i][k.strip()] = [row[k]]
            while len(row_to_merge) > 0:  # there are still entries to merge
                mappings.warn(f"Duplicate row for {merged_dict[i][identifier][0]} in {page}")
                row = row_to_merge.pop(0)
                for k in row.keys():
                    merged_dict[i][k.strip()].append(row[k])
            # for the identifier key, just pick one, since they're all the same:
            merged_dict[i][identifier] = merged_dict[i][identifier].pop()

        # Now we can clean up the dicts: index them by identifier instead of int
        indexed_merged_dict = {}
        for i in range(0, len(merged_dict.keys())):
            indiv = merged_dict[i][identifier]
            indexed_merged_dict[indiv] = merged_dict[i]
            if indiv not in individuals:
                individuals.append(indiv)
        final_merged[page] = indexed_merged_dict

    return {
        "identifier": identifier,
        "columns": cols_index,
        "individuals": individuals,
        "data": final_merged
    }


def map_row_to_mcodepacket(identifier, indexed_data, node):
    """Given a particular individual's data, and a node in the schema, return the node with mapped data."""
    if "str" in str(type(node)) and node != "":
        return eval_mapping(identifier, indexed_data, node)
    elif "list" in str(type(node)):
        new_node = []
        for item in node:
            m = map_row_to_mcodepacket(identifier, indexed_data, item)
            if "list" in str(type(m)):
                new_node = m
            else:
                new_node.append(m)
        return new_node
    elif "dict" in str(type(node)):
        scaffold = {}
        for key in node.keys():
            x = map_row_to_mcodepacket(identifier, indexed_data, node[key])
            if x is not None:
                scaffold[key] = x
        return scaffold


def translate_mapping(identifier, indexed_data, mapping):
    """Given the identifier field, the data, and a particular mapping, figure out what the method and the mapped values are."""
    func_match = re.match(r".*\{(.+?)\((.+)\)\}.*", mapping)
    if func_match is not None:  # it's a function, prep the dictionary and exec it
        items = func_match.group(2).split(";")
        new_dict = {}
        mappings.IDENTIFIER = {"id": identifier}
        for item in items:
            item = item.strip()
            sheets = None
            sheet_match = re.match(r"(.+?)\.(.+)", item)
            if sheet_match is not None:
                # this is a specific item on a specific sheet:
                item = sheet_match.group(2)
                sheets = [sheet_match.group(1).replace('"', '').replace("'", "")]
            # check to see if this item is even present in the columns:
            if item in indexed_data["columns"]:
                new_dict[item] = {}
                if sheets is None:
                    # look for all sheets that match this item name:
                    sheets = indexed_data["columns"][item]
                for sheet in sheets:
                    # for each of these sheets, add this identifier's contents as a key and array:
                    if identifier in indexed_data["data"][sheet]:
                        new_dict[item][sheet] = indexed_data["data"][sheet][identifier][item]
                    else:
                        new_dict[item][sheet] = []
        return func_match.group(1), new_dict
    return None, None


def eval_mapping(identifier, indexed_data, node):
    """Given the identifier field, the data, and a particular schema node, evaluate the mapping and return the final JSON for the node in the schema."""
    method, mapping = translate_mapping(identifier, indexed_data, node)
    if method is not None:
        if "mappings" not in mappings.MODULES:
            mappings.MODULES["mappings"] = importlib.import_module("mappings")
        module = mappings.MODULES["mappings"]
        # is the function something in a dynamically-loaded module?
        subfunc_match = re.match(r"(.+)\.(.+)", method)
        if subfunc_match is not None:
            module = mappings.MODULES[subfunc_match.group(1)]
            method = subfunc_match.group(2)
        return eval(f'module.{method}({mapping})')


def ingest_redcap_data(input_path):
    """Test of ingest of redcap output files"""
    raw_csv_dfs = {}
    outputfile = "mohpacket"
    if os.path.isdir(input_path):
        output_file = os.path.normpath(input_path)
        files = os.listdir(input_path)
        for file in files:
            print(f"Reading input file {file}")
            file_match = re.match(r"(.+)\.csv$", file)
            if file_match is not None:
                df = pandas.read_csv(os.path.join(input_path, file), dtype=str, encoding = "latin-1")
                #print(f"initial df shape: {df.shape}")
                # find and drop empty columns
                empty_cols = [col for col in df if df[col].isnull().all()]  
                print(f"Dropped {len(empty_cols)} empty columns")
                df = df.drop(empty_cols, axis=1)
                print(f"final df shape: {df.shape}")
                raw_csv_dfs[file_match.group(1)] = df 
    return raw_csv_dfs, output_file

def ingest_raw_data(input_path, indexed):
    """Ingest the csvs or xlsx and create dataframes for processing."""
    raw_csv_dfs = {}
    output_file = "mCodePacket"
    # input can either be an excel file or a directory of csvs
    if os.path.isfile(input_path):
        file_match = re.match(r"(.+)\.xlsx$", input_path)
        if file_match is not None:
            output_file = file_match.group(1)
            df = pandas.read_excel(input_path, sheet_name=None, dtype=str)
            for page in df:
                raw_csv_dfs[page] = df[page]  # append all processed mcode dataframes to a list
    elif os.path.isdir(input_path):
        output_file = os.path.normpath(input_path)
        files = os.listdir(input_path)
        for file in files:
            file_match = re.match(r"(.+)\.csv$", file)
            if file_match is not None:
                df = pandas.read_csv(os.path.join(input_path, file), dtype=str)
                raw_csv_dfs[file_match.group(1)] = df
    if indexed is not None and len(indexed) > 0:
        for df in indexed:
            df = df.replace(".csv","")
            raw_csv_dfs[df].reset_index(inplace=True)
    return raw_csv_dfs, output_file

def process_mapping(line, test=False):
    """Given a csv mapping line, process into its component pieces."""
    line_match = re.match(r"(.+?),(.*$)", line.replace("\"", ""))
    if line_match is not None:
        element = line_match.group(1)
        value = ""
        if test:
            value = "test"
        if line_match.group(2) != "" and not line_match.group(2).startswith("##"):
            value = line_match.group(2).replace(",", ";")
        elems = element.replace("*", "").replace("+", "").split(".")
        return value, elems
    return line, None


def create_mapping_scaffold(lines, test=False):
    """Given lines from a mapping csv file, create a scaffold mapping dict."""
    props = {}
    for line in lines:
        if line.startswith("#"):
            continue
        if re.match(r"^\s*$", line):
            continue
        value, elems = process_mapping(line, test)
        if elems is not None:
            x = elems.pop(0)
            if x not in props:
                props[x] = []
            if len(elems) > 0:
                props[x].append(".".join(elems)+","+value)
            elif value != "":
                props[x].append(value)
            else:
                props[x] = []
        else:
            return line

    # clear out the empty keys:
    empty_keys = []
    for key in props.keys():
        if len(props[key]) == 0:
            empty_keys.append(key)
        if len(props[key]) == 1 and props[key][0] == '0,':
            empty_keys.append(key)
    for key in empty_keys:
        props.pop(key)

    for key in props.keys():
        if key == "0":  # this could map to a list
            y = create_mapping_scaffold(props[key])
            if y is not None:
                return [y]
            return None
        props[key] = create_mapping_scaffold(props[key])

    if len(props.keys()) == 0:
        return None
    
    return props


def load_manifest(mapping):
    """Given a manifest file's path, return the data inside it."""
    identifier = None
    schema = "mcode"
    mapping_scaffold = None
    indexed = None
    with open(mapping, 'r') as f:
        manifest_dir = os.path.dirname(os.path.abspath(mapping))
        manifest = yaml.safe_load(f)
    if manifest is None:
        print("Manifest file needs to be in YAML format")
        return
    if "identifier" in manifest:
        identifier = manifest["identifier"]
    if "schema" in manifest:
        schema = manifest["schema"]
    if "mapping" in manifest:
        mapping_path = os.path.join(manifest_dir, manifest["mapping"])
        if os.path.isabs(manifest["mapping"]):
            mapping_path = manifest["mapping"]
        mapping = []
        with open(mapping_path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("#"):
                    continue
                if re.match(r"^\s*$", line):
                    continue
                mapping.append(line)
        mapping_scaffold = create_mapping_scaffold(mapping)
    if "functions" in manifest:
        for mod in manifest["functions"]:
            try:
                mod_path = os.path.join(manifest_dir, mod)
                if not mod_path.endswith(".py"):
                    mod_path += ".py"
                spec = importlib.util.spec_from_file_location(mod, mod_path)
                mappings.MODULES[mod] = importlib.util.module_from_spec(spec)
                sys.modules[mod] = mappings.MODULES[mod]
                spec.loader.exec_module(mappings.MODULES[mod])
            except Exception as e:
                print(e)
                return
                # mappings is a standard module: add it
    mappings.MODULES["mappings"] = importlib.import_module("mappings")
    if "indexed" in manifest:
        indexed = manifest["indexed"]
    return {
        "identifier": identifier,
        "schema": schema,
        "scaffold": mapping_scaffold,
        "mapping": mapping,
        "indexed": indexed
    }


def main(args):
    input_path = args.input
    manifest_file = args.manifest
    mappings.VERBOSE = args.verbose
    
    # read manifest data and create a mapping scaffold
    # from the template file specififed inside
    manifest = load_manifest(manifest_file)
    identifier = manifest["identifier"]
    #schema = manifest["schema"]
    mapping_scaffold = manifest["scaffold"]
    indexed = manifest["indexed"]
    if identifier is None:
        print("Need to specify what the main identifier column name is in the manifest file")
        return
    if mapping_scaffold is None:
        print("Could not create mapping scaffold. Make sure that the manifest specifies a valid mapping template.")
        return

    raw_csv_dfs = ingest_redcap_data(input_path)
    return

    if input_path is not None:
        raw_csv_dfs, output_file = ingest_raw_data(input_path, indexed)
        if not raw_csv_dfs:
            print(f"No ingestable files (csv or xlsx) were found at {input_path}")
            return
    else:
        print("An input file (or directory of input csvs) is required, using the --input argument")
        return

    indexed_data = process_data(raw_csv_dfs, identifier)
    with open(f"{output_file}_indexed.json", 'w') as f:
        json.dump(indexed_data, f, indent=4)

    # if verbose flag is set, warn if column name is present in multiple sheets:
    for col in indexed_data["columns"]:
        if col != identifier and len(indexed_data["columns"][col]) > 1:
            mappings.warn(f"Column name {col} present in multiple sheets: {', '.join(indexed_data['columns'][col])}")

    mcodepackets = []

    # for each identifier's row, make an mcodepacket
    for key in indexed_data["individuals"]:
        print(f"Creating packet for {key}")
        mcodepackets.append(map_row_to_mcodepacket(key, indexed_data, deepcopy(mapping_scaffold)))

    # special case: if it was candigv1, we need to wrap the results in "metadata"
    # if schema == "candigv1":
    #     mcodepackets = {"metadata": mcodepackets}

    with open(f"{output_file}_map.json", 'w') as f:    # write to json file for ingestion
        json.dump(mcodepackets, f, indent=4)


if __name__ == '__main__':
    main(parse_args())
