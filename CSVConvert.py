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

from moh_mappings import mohschema
from generate_schema import generate_mapping_template

VERBOSE = False
IDENTIFIER_KEY = None

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required = True, help="Path to either an xlsx file or a directory of csv files for ingest")
    # parser.add_argument('--api_key', type=str, help="BioPortal API key found in BioPortal personal account settings")
    # parser.add_argument('--email', type=str, help="Contact email to access NCBI clinvar API. Required by Entrez")
    #parser.add_argument('--schema', type=str, help="Schema to use for template; default is mCodePacket")
    parser.add_argument('--manifest', type=str, required = True, help="Path to a manifest file describing the mapping."
                                                                  " See README for more information")
    parser.add_argument('--verbose', '--v', action="store_true", help="Print extra information")
    args = parser.parse_args()
    return args


def process_data(raw_csv_dfs, identifier):
    """Takes a set of raw dataframes with a common identifier and merges into a  JSON data structure."""
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

def map_row_to_mcodepacket(identifier, index_field, indexed_data, node, x):
    """
    Given a particular individual's data, and a node in the schema, return the node with mapped data. Recursive.
    If x is not None, it is an index into an object that is part of an array.
    """
    if "dict" in str(type(node)) and "INDEX" in node:
        index_field = node["INDEX"]
        node = node["NODES"]
        result = []
        if index_field is not None:
            # create a new indexed_data for this array of objects:
            # find the sheet that the index_field is on:
            if index_field in indexed_data["columns"] and len(indexed_data["columns"][index_field]) == 1:
                sheet = indexed_data["columns"][index_field][0]
                new_data = deepcopy(indexed_data["data"][sheet][identifier])
                new_sheet = f"INDEX_{sheet}_{identifier}"
                global IDENTIFIER_KEY
                if IDENTIFIER_KEY in new_data:
                    new_data.pop(IDENTIFIER_KEY)
                # for each index_field value, create a new object of data
                if "INDEX" not in indexed_data["columns"]:
                    indexed_data["columns"]["INDEX"] = []
                indexed_data["columns"]["INDEX"].append(new_sheet)
                indexed_data["data"][new_sheet] = {}
                new_ids = new_data.pop(index_field)
                for i in range(0,len(new_ids)):
                    new_ident_dict = {}
                    for key in new_data.keys():
                        new_ident_dict[f"{sheet}.{key}"] = new_data[key][i]
                    indexed_data["data"][new_sheet][new_ids[i]] = new_ident_dict
                    result.append(map_row_to_mcodepacket(identifier, index_field, indexed_data, node, new_ids[i]))
                return result
            else:
                raise Exception(f"couldn't identify index_field {index_field}")
    if "str" in str(type(node)) and node != "":
        if VERBOSE:
            print(f"Str {identifier},{index_field},{node}")
        return eval_mapping(identifier, index_field, indexed_data, node, x)
    if "list" in str(type(node)):
        if VERBOSE:
            print(f"List {node}")
        # if we get here with a node that can be a list (e.g. Treatments)
        new_node = []
        for item in node:
            if VERBOSE:
                print(f"Mapping list item {item}")
            m = map_row_to_mcodepacket(identifier, index_field, indexed_data, item, x)
            if "list" in str(type(m)):
                new_node = m
            else:
                if VERBOSE:
                    print(f"Appending {m}")
                new_node.append(m)
        return new_node
    elif "dict" in str(type(node)):
        scaffold = {}
        for key in node.keys():
            if VERBOSE:
                print(f"\nKey {key}")
            dict = map_row_to_mcodepacket(identifier, index_field, indexed_data, node[key], x)
            if dict is not None:
                scaffold[key] = dict
        return scaffold


def translate_mapping(identifier, index_field, indexed_data, mapping):
    """Given the identifier field, the data dict, and a particular mapping from
    the template file, parse out the mapping method and get the matching data."""

    # split the mapping into the function name and the raw data fields that
    # are the parameters
    # e.g. {single_val(submitter_donor_id)} -> match.group(1) = single_val
    # and match.group(2) = submitter_donor_id (may be multiple fields)
    func_match = re.match(r".*\{(.+?)\((.+)\)\}.*", mapping)
    if func_match is not None:  # it's a function, prep the dictionary and exec it
        # get the fields that are the params; separator is a semicolon because
        # we replaced the commas back in process_mapping
        items = func_match.group(2).split(";")
        data_values, items = get_data_for_fields(identifier, index_field, indexed_data, items)
        if "INDEX" in items:
            items.remove("INDEX")
        return func_match.group(1), data_values, items
    # else: # try and match the field name exactly
    #     data_values = get_data_for_fields(identifier, indexed_data,[key])
    #     if data_values is not None:
    #         return None, data_values
    return None, None, None

def get_data_for_fields(identifier, index_field, indexed_data, fields):
    """
    Given a list of fields and the indexed_data, return a dictionary of the
    values for each field.
    If index_field is not None, create an INDEX key that lists all the possible values that could use
    """
    data_values = {}
    items = []
    if index_field is not None:
        fields.append("INDEX")
    for item in fields:
        item = item.strip()
        sheets = None
        sheet_match = re.match(r"(.+?)\.(.+)", item)
        if sheet_match is not None:
            # this is a specific item on a specific sheet:
            item = sheet_match.group(2)
            sheets = [sheet_match.group(1).replace('"', '').replace("'", "")]
        # check to see if this item is even present in the columns:
        if item in indexed_data["columns"]:
            items.append(item)
            data_values[item] = {}
            if sheets is None:
                # look for all sheets that match this item name:
                sheets = indexed_data["columns"][item]
            for sheet in sheets:
                # for each of these sheets, add this identifier's contents as a key and array:
                if identifier in indexed_data["data"][sheet]:
                    data_value = indexed_data["data"][sheet][identifier][item]
                    data_values[item][sheet] = data_value
                elif item == "INDEX":
                    data_values[item][sheet] = indexed_data["data"][sheet]
                else:
                    data_values[item][sheet] = []
    if "INDEX" in items:
        items.remove("INDEX")
    return data_values, items

def eval_mapping(identifier, index_field, indexed_data, node, x):
    """
    Given the identifier field, the data, and a particular schema node, evaluate
    the mapping using the provider method and return the final JSON for the node
    in the schema.
    If x is not None, it is an index into an object that is part of an array.
    """
    method, data_values, items = translate_mapping(identifier, index_field, indexed_data, node)
    if "mappings" not in mappings.MODULES:
        mappings.MODULES["mappings"] = importlib.import_module("mappings")
    if method is not None:
        module = mappings.MODULES["mappings"]
        # is the function something in a dynamically-loaded module?
        subfunc_match = re.match(r"(.+)\.(.+)", method)
        if subfunc_match is not None:
            module = mappings.MODULES[subfunc_match.group(1)]
            method = subfunc_match.group(2)
    else:
        module = mappings.MODULES["mappings"]
        method = "single_val"
        data_values, items = get_data_for_fields(identifier, index_field, indexed_data, [node])
    if "INDEX" in data_values:
        # find all the relevant keys in index_field:
        for node in items:
            for sheet in data_values[node]:
                index_identifier = f"INDEX_{sheet}_{identifier}"
                new_node_val = data_values["INDEX"][index_identifier][x][f"{sheet}.{node}"]
                data_values[node][sheet] = new_node_val
    try:
        if "INDEX" in data_values:
            data_values.pop("INDEX")
        # check to see if there are even any data values besides INDEX:
        if len(data_values.keys()) > 0:
            return eval(f'module.{method}({data_values})')
    except mappings.MappingError as e:
        print(f"Error evaluating {method}")
        raise


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
    """Given a csv mapping line, process into its component pieces.
    Turns treatment_type, {list_val(Treatment.submitter_treatment_id)} into
    {list_val(Treatment.submitter_treatment_id)},['treatment_type']."""
    line_match = re.match(r"(.+?),(.*$)", line.replace("\"", ""))
    if line_match is not None:
        element = line_match.group(1)
        value = ""
        if test:
            value = "test"
        if line_match.group(2) != "":
            test_value = line_match.group(2).strip()
            if not test_value.startswith("##"):
                # replace comma separated parameter list with semicolon separated
                value = test_value.replace(",", ";")
        # strip off the * (required field) and + (ontology term) notations
        # TODO - check required fields
        elems = element.replace("*", "").replace("+", "").split(".")
        return value, elems
    return line, None

def read_mapping_template(mapping_path):
    """Given a path to a mapping template file, read the lines and
    return them as an array."""
    template_lines = []
    try:
        with open(mapping_path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("#"):
                    continue
                if re.match(r"^\s*$", line):
                    continue
                template_lines.append(line)
    except FileNotFoundError:
        print(f"Mapping template {mapping_path} not found")

    return template_lines

def create_scaffold_from_template(lines, test=False):
    """Given lines from a template mapping csv file, create a scaffold
    mapping dict."""
    props = {}
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            # this line is a comment, skip it
            continue
        if re.match(r"^\s*$", line):
            #print(f"skipping {line}")
            continue
        value, elems = process_mapping(line, test)
        # elems are the first column in the csv, the parts of the schema field,
        # i.e. Treatment.id becomes [Treatment, id]. value is the mapping function
        if elems is not None:
            # we are creating an array for schema field
            # where each element is a string of "child field,mapping function"
            # or just "mapping function" if no children
            x = elems.pop(0)
            if x not in props:
                # not seen yet, add empty list
                props[x] = []
            if len(elems) > 0:
                tempvar=(".".join(elems)+","+value)
                #print(f"Appending tempvar {tempvar} to props for {x} : {line}")
                props[x].append(".".join(elems)+","+value)
            elif value != "":
                #print(f"Appending value {value} to props for {x} : {line}")
                props[x].append(value)
            else:
                #print(f"How do we get here, {x}, adding empty list : {line}")
                props[x] = [x]
            #print(f"Now {props[x]} for {x}")
        else:
            return line

    # clear out the keys that just have empty lists (or just a single '0')
    # empty_keys = []
    # for key in props.keys():
    #     if len(props[key]) == 0:
    #         empty_keys.append(key)
    #     if len(props[key]) == 1 and props[key][0] == '0,':
    #         print(f"did we get here for {key}?")
    #         empty_keys.append(key)
    # for key in empty_keys:
    #     props.pop(key)
    #print(f"Cleared empty keys {empty_keys}")

    # print(f"Props:")
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(props)

    for key in props.keys():
        if key == "0":  # this could map to a list
            index = None
            first_key = props[key].pop(0)
            index_match = re.match(r"\{indexed_on\((.+)\)\}", first_key)
            if index_match is not None:
                index = index_match.group(1)
            else:
                props[key].insert(0, first_key)
            # print(f"Found array element {props[key]}")
            y = create_scaffold_from_template(props[key])
            # print(f"What is {y}")
            if y is not None:
                # return [y]
                return {"INDEX": index, "NODES": y}
            return None
        props[key] = create_scaffold_from_template(props[key])

    if len(props.keys()) == 0:
        return None

    return props


def load_manifest(manifest_file):
    """Given a manifest file's path, return the data inside it."""
    identifier = None
    schema = "mcode"
    mapping_path = None
    indexed = None
    with open(manifest_file, 'r') as f:
        manifest = yaml.safe_load(f)
    if manifest is None:
        print("Manifest file needs to be in YAML format")
        return

    if "identifier" in manifest:
        identifier = manifest["identifier"]
    if "schema" in manifest:
        schema = manifest["schema"]
    if "mapping" in manifest:
        mapping_file = manifest["mapping"]
        manifest_dir = os.path.dirname(os.path.abspath(manifest_file))
        mapping_path = os.path.join(manifest_dir, mapping_file)
        if os.path.isabs(mapping_file):
            mapping_path = manifest_file

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
        "mapping": mapping_path,
        "indexed": indexed
    }


def interpolate_mapping_into_scaffold(mapped_template, scaffold_template):
    scaffold_keys = list(map(lambda x: x.split(",")[0].strip(), scaffold_template))
    for mapped_line in mapped_template:
        mapped_key = mapped_line.split(",")[0].strip()
        if mapped_key in scaffold_keys:
            scaffold_template[scaffold_keys.index(mapped_key)] = mapped_line
    return scaffold_template


def main(args):
    input_path = args.input
    manifest_file = args.manifest
    mappings.VERBOSE = args.verbose
    VERBOSE = args.verbose

    # read manifest data
    manifest = load_manifest(manifest_file)
    identifier = manifest["identifier"]
    indexed = manifest["indexed"]
    if identifier is None:
        print("Need to specify what the main identifier column name as 'identifier' in the manifest file")
        return
    global IDENTIFIER_KEY
    IDENTIFIER_KEY = identifier

    # read the schema (from the url specified in the manifest) and generate
    # a scaffold
    schema = mohschema(manifest["schema"])
    if schema is None:
        print(f"Did not find an openapi schema at {url}; please check link")
        return
    scaffold = schema.generate_scaffold()
    sc, mapping_template = generate_mapping_template(schema.generate_schema_array()["DonorWithClinicalData"])

    schema_list = list(scaffold)
    if VERBOSE:
        print(f"Imported schemas: {schema_list} from mohschema")


    # read the mapping template (contains the mapping function for each
    # field)
    template_lines = read_mapping_template(manifest["mapping"])

    ## Replace the lines in the original template with any matching lines in template_lines
    #interpolate_mapping_into_scaffold(template_lines, mapping_template)
    # mapping_scaffold = create_scaffold_from_template(mapping_template)

    mapping_scaffold = create_scaffold_from_template(template_lines)

    # print("Scaffold from template")
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(mapping_scaffold)
    if mapping_scaffold is None:
        print("Could not create mapping scaffold. Make sure that the manifest specifies a valid csv template.")
        return

    # # read the raw data
    print("Reading raw data")
    raw_csv_dfs, output_file = ingest_raw_data(input_path, indexed)
    if not raw_csv_dfs:
        print(f"No ingestable files (csv or xlsx) were found at {input_path}")
        return

    print("Indexing data")
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
        mcodepackets.append(map_row_to_mcodepacket(
            key, None, indexed_data, deepcopy(mapping_scaffold), None)
            )

    # # special case: if it was candigv1, we need to wrap the results in "metadata"
    # # if schema == "candigv1":
    # #     mcodepackets = {"metadata": mcodepackets}

    with open(f"{output_file}_indexed.json", 'w') as f:
        json.dump(indexed_data, f, indent=4)

    with open(f"{output_file}_map.json", 'w') as f:    # write to json file for ingestion
        json.dump(mcodepackets, f, indent=4)


if __name__ == '__main__':
    main(parse_args())
