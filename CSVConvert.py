#!/usr/bin/env python
# coding: utf-8

from copy import deepcopy
import importlib.util
import json
import mappings
import os
import pandas
import re
import sys
import yaml
import argparse

from mohschema import MoHSchema


def verbose_print(message):
    if mappings.VERBOSE:
        print(message)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required = True, help="Path to either an xlsx file or a directory of csv files for ingest")
    # parser.add_argument('--api_key', type=str, help="BioPortal API key found in BioPortal personal account settings")
    # parser.add_argument('--email', type=str, help="Contact email to access NCBI clinvar API. Required by Entrez")
    #parser.add_argument('--schema', type=str, help="Schema to use for template; default is mCodePacket")
    parser.add_argument('--manifest', type=str, required = True, help="Path to a manifest file describing the mapping."
                                                                  " See README for more information")
    parser.add_argument('--test', action="store_true", help="Use exact template specified in manifest: do not remove extra lines")
    parser.add_argument('--verbose', '--v', action="store_true", help="Print extra information")
    args = parser.parse_args()
    return args


def map_data_to_scaffold(node, line, rownum):
    """
    Given a particular individual's data, and a node in the schema, return the node with mapped data. Recursive.
    """
    if line is not None:
        mappings.CURRENT_LINE = line
        verbose_print(f"Mapping line '{mappings.CURRENT_LINE}' for {mappings.IDENTIFIER}")
    # if we're looking at an array of objects:
    if "dict" in str(type(node)) and "INDEX" in node:
        result = map_indexed_scaffold(node, line)
        if result is not None and len(result) == 0:
            return None
        return result
    if "str" in str(type(node)) and node != "":
        result = eval_mapping(node, rownum)
        verbose_print(f"Evaluated result is {result}, {node}, {rownum}")
        return result
    if "dict" in str(type(node)):
        result = {}
        for key in node.keys():
            linekey = key
            if line is not None:
                linekey = f"{line}.{key}"
            dict = map_data_to_scaffold(node[key], f"{linekey}", rownum)
            if dict is not None:
                result[key] = dict
        if result is not None and len(result) == 0:
            return None
        return result


def map_indexed_scaffold(node, line):
    """
    Given a node that is indexed on some array of values, populate the array with the node's values.
    """
    result = []
    index_values = None
    # process the index
    if "INDEX" in node:
        index_method, index_field = parse_mapping_function(node["INDEX"])
        verbose_print(f"  Mapping indexed scaffold for {index_field}")
        if index_field is None:
            return None
        # evaluate INDEX, using None as rownum to indicate that we're calculating an index and not a specific row
        index_values = eval_mapping(node["INDEX"], None)
        verbose_print(f"  Indexing on  {index_values}")
        if index_values is None:
            return None
        index_field = index_values["field"]
        index_sheet = index_values["sheet"]
        index_values = index_values["values"]
    else:
        raise Exception(f"An indexed_on notation is required for {line}")

    # only process if there is data for this IDENTIFIER in the index_sheet
    if mappings.IDENTIFIER in mappings.INDEXED_DATA['data'][index_sheet]:
        if index_values is not None:
        #     # add this new indexed value into the indexed_data table
            mappings.INDEXED_DATA['data'][index_sheet][mappings.IDENTIFIER][index_field] = index_values
        top_frame = mappings._peek_at_top_of_stack()

        # FIRST PASS: when we've passed in None for the sheet in the stack
        if top_frame["sheet"] is None:
            mappings.INDEX_STACK[-1]["sheet"] = index_sheet
            mappings.INDEX_STACK[-1]["id"] = index_field
            top_frame = mappings._peek_at_top_of_stack()

        row = get_row_for_stack_top(top_frame["sheet"], top_frame["rownum"])
        verbose_print(f"  Comparing to index_values {index_values} to top_frame {row[index_field]}")

        possible_values = []

        # for each value in index_sheet.index_field, is it in index_values?
        for i in range(0, len(index_values)):
            if index_values[i] == row[index_field]:
                possible_values.append(index_values[i])
            else:
                possible_values.append(None)
        verbose_print(f"  Possible values are {possible_values}")

        if index_values is not None:
            for i in range(0, len(possible_values)):
                mappings._push_to_stack(index_sheet, index_field, i)
                index_val = possible_values[i]
                verbose_print(f"  Mapping {i}th row for {possible_values}")
                if index_val is not None:
                    sub_res = map_data_to_scaffold(node["NODES"], f"{line}.INDEX", i)
                    if sub_res is not None:
                        result.append(sub_res)
                else:
                    verbose_print(f"  Skipping {i}th row")
                mappings._pop_from_stack()
    if len(result) == 0:
        return None
    return result


def parse_sheet_from_field(param):
    """
    If the parameter specifies a sheet, return just that sheet and the parameter's base name.
    Returns None, None if the parameter is not found.
    """
    if param is None:
        return None, None
    param = param.strip()

    sheet = None
    # possible matches for sheet/column:
    # ((\"|\')(.+?)\2)\.((\"|\')(.+)\5): "MOH.CCN"."treatment.id" (group 3).(group 6)
    # ((\"|\')(.+?)\2)\.(.+): "MOH.CCN".treatment_id (group 1).(group 3)
    # (.+?)\.((\"|\')(.+)\3): MOH_CCN.'treatment.id' (group 1).(group 3)
    sheet_match = re.match(r"((\"|\')(.+?)\2)\.((\"|\')(.+)\5)", param)
    if sheet_match is not None:
        sheet = sheet_match.group(3)
        param = sheet_match.group(6)
    if sheet is None:
        sheet_match = re.match(r"((\"|\')(.+?)\2)\.(.+)", param)
        if sheet_match is not None:
            sheet = sheet_match.group(3)
            param = sheet_match.group(4).replace('"', "").replace("'", "")
    if sheet is None:
        sheet_match = re.match(r"(.+?)\.(.+)", param)
        if sheet_match is not None:
            sheet = sheet_match.group(1)
            param = sheet_match.group(2)
    if sheet is not None:
        if param in mappings.INDEXED_DATA["columns"]:
            if sheet in mappings.INDEXED_DATA["columns"][param]:
                return param, sheet
            return None, None
    if param in mappings.INDEXED_DATA["columns"]:
        if len(mappings.INDEXED_DATA["columns"][param]) > 1:
            mappings._warn(f"There are multiple sheets that contain column name {param}. Please specify the exact sheet in the mapping.")
        return param, mappings.INDEXED_DATA["columns"][param][0]
    return None, None


def parse_mapping_function(mapping):
    # split the mapping into the function name and the raw data fields that
    # are the parameters
    # e.g. {single_val(submitter_donor_id)} -> match.group(1) = single_val
    # and match.group(2) = submitter_donor_id (may be multiple fields)

    method = None
    parameters = None
    func_match = re.match(r".*\{(.+?)\((.+)\)\}.*", mapping)
    if func_match is not None:  # it's a function, prep the dictionary and exec it
        # get the fields that are the params; separator is a semicolon because
        # we replaced the commas back in process_mapping
        method = func_match.group(1)
        parameters = func_match.group(2).split(";")
        parameters = list(map(lambda x: x.strip(), parameters))
    return method, parameters


def get_row_for_stack_top(sheet, rownum):
    result = {}
    for param in mappings.INDEXED_DATA["data"][sheet][mappings.IDENTIFIER].keys():
        result[param] = mappings.INDEXED_DATA["data"][sheet][mappings.IDENTIFIER][param][rownum]
    verbose_print(f"get_row_for_stack_top is {result}")
    return result


def populate_data_for_params(params, rownum):
    """
    Given a list of params, return a dictionary of the
    values for each parameter.
    """
    data_values = {}
    for param in params:
        param, sheet = parse_sheet_from_field(param)
        if param is None:
            return None
        if sheet is None:
            verbose_print(f"  WARNING: parameter {param} is not present in the input data")
        else:
            # there should only be one sheet
            verbose_print(f"  populating data for {param} in {sheet}")
            if param not in data_values:
                data_values[param] = {}
            # add this identifier's contents as a key and array:
            if mappings.IDENTIFIER in mappings.INDEXED_DATA["data"][sheet]:
                data_values[param][sheet] = deepcopy(mappings.INDEXED_DATA["data"][sheet][mappings.IDENTIFIER][param])
                top_frame = mappings._peek_at_top_of_stack()

                # if rownum is None, we are calculating an index. We expect to return a bunch of relevant values.
                # if rownum is not None, we are working with a particular indexed value: we should filter to just that value.
                if rownum is not None:
                    row = get_row_for_stack_top(top_frame["sheet"], rownum)
                    if top_frame["sheet"] == sheet:
                        for i in range(0, len(data_values[param][sheet])):
                            if row[param] is None or row[param] != data_values[param][sheet][i]:
                                data_values[param][sheet][i] = None
                        data_values[param][sheet] = data_values[param][sheet][rownum]
                        verbose_print(f"  populated single value {data_values[param][sheet]}")
                    else:
                        verbose_print(f"  populated non-indexed value {data_values[param][sheet]}")
                else:
                    verbose_print(f"  populated index value {data_values[param][sheet]}")
            else:
                verbose_print(f"  WARNING: {mappings.IDENTIFIER} not on sheet {sheet}")
                data_values[param][sheet] = []
    return data_values

def eval_mapping(node_name, rownum):
    """
    Given the identifier field, the data, and a particular schema node, evaluate
    the mapping using the provider method and return the final JSON for the node
    in the schema.
    """
    verbose_print(f"  Evaluating {mappings.IDENTIFIER}: {node_name}")
    if "mappings" not in mappings.MODULES:
        mappings.MODULES["mappings"] = importlib.import_module("mappings")
    modulename = "mappings"

    method, parameters = parse_mapping_function(node_name)
    data_values = populate_data_for_params(parameters, rownum)
    if data_values is None:
        return None
    if method is not None:
        # is the function something in a dynamically-loaded module?
        subfunc_match = re.match(r"(.+)\.(.+)", method)
        if subfunc_match is not None:
            modulename = subfunc_match.group(1)
            method = subfunc_match.group(2)
        verbose_print(f"  Using method {modulename}.{method}({', '.join(parameters)}) with {data_values}")
        try:
            if len(data_values.keys()) > 0:
                module = mappings.MODULES[modulename]
                return eval(f'module.{method}({data_values})')
        except mappings.MappingError as e:
            print(f"Error evaluating {method}")
            raise e
    return None


def ingest_raw_data(input_path):
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
    return raw_csv_dfs, output_file


def process_data(raw_csv_dfs):
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
        df.set_index(mappings.IDENTIFIER_FIELD, inplace=True)
        df.sort_index(inplace=True)
        df.reset_index(inplace=True)
        dups = df.duplicated(subset=[mappings.IDENTIFIER_FIELD], keep='first')

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
                rows_to_merge[df_dict[index][mappings.IDENTIFIER_FIELD]] = [df_dict[index]]
            else:
                rows_to_merge[df_dict[index][mappings.IDENTIFIER_FIELD]].append(df_dict[index])
        merged_dict = {}  # this is going to be the dict with arrays:
        for i in range(0, len(rows_to_merge)):
            merged_dict[i] = {}
            row_to_merge = rows_to_merge[list(rows_to_merge.keys())[i]]
            while len(row_to_merge) > 0:  # there are still entries to merge
                row = row_to_merge.pop(0)
                for k in row.keys():
                    if k.strip() not in merged_dict[i]:
                        merged_dict[i][k.strip()] = []
                    val = row[k]
                    if val == 'nan':
                        val = None
                    merged_dict[i][k.strip()].append(val)
                if len(row_to_merge) > 0:
                    mappings._warn(f"Duplicate row for {merged_dict[i][mappings.IDENTIFIER_FIELD][0]} in {page}")

        # Now we can clean up the dicts: index them by identifier instead of int
        indexed_merged_dict = {}
        for i in range(0, len(merged_dict.keys())):
            indiv = merged_dict[i][mappings.IDENTIFIER_FIELD][0]
            indexed_merged_dict[indiv] = merged_dict[i]
            if indiv not in individuals:
                individuals.append(indiv)
        final_merged[page] = indexed_merged_dict

    return {
        "identifier_field": mappings.IDENTIFIER_FIELD,
        "columns": cols_index,
        "individuals": individuals,
        "data": final_merged
    }


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

    # clear out the keys that just have empty lists (or just a single 'INDEX')
    # empty_keys = []
    # for key in props.keys():
    #     if len(props[key]) == 0:
    #         empty_keys.append(key)
    #     if len(props[key]) == 1 and props[key][0] == 'INDEX,':
    #         print(f"did we get here for {key}?")
    #         empty_keys.append(key)
    # for key in empty_keys:
    #     props.pop(key)
    #print(f"Cleared empty keys {empty_keys}")

    for key in props.keys():
        if key == "INDEX":  # this maps to a list
            first_key = props[key].pop(0)
            y = create_scaffold_from_template(props[key])
            return {"INDEX": first_key, "NODES": y}
        props[key] = create_scaffold_from_template(props[key])

    if len(props.keys()) == 0:
        return None

    return props


def scan_template_for_duplicate_mappings(template_lines):
    field_map = {}
    for line in template_lines:
        line_match = re.match(r"(.+), *\{(.+)\}", line)
        if line_match is not None:
            template_line = line_match.group(1)
            val = line_match.group(2).strip()
            if val not in field_map:
                field_map[val] = []
            field_map[val].append(template_line)
                # else:
                #     print(f"WARNING: No parameter '{val}' exists")
    data_values = list(field_map.keys())
    for dv in data_values:
        indices = []
        for i in field_map[dv]:
            if i.endswith("INDEX"):
                indices.append(i)
        if len(indices) == 0:
            field_map.pop(dv)
        else:
            field_map[dv] = indices
    data_values = list(field_map.keys())
    for dv in data_values:
        if len(field_map[dv]) == 1:
            field_map.pop(dv)
    # if the last two bits in each dv are the same, this is a dup
    data_values = list(field_map.keys())
    for dv in data_values:
        if dv != 'indexed_on(NONE)':
            indexed_on = []
            for i in field_map[dv]:
                bits = i.split(".")
                indexed_on.append(".".join(bits[len(bits)-2:len(bits)-1]))
            uniques = list(set(indexed_on))
            for u in range(0,len(uniques)):
                count = 0
                for i in range(0,len(indexed_on)):
                    if uniques[u] == indexed_on[i]:
                        count += 1
                if count > 1:
                    msg = f"ERROR: Key {dv} can only be used to index one line. If one of these duplicates does not have an index, use {{indexed_on(NONE)}}:\n"
                    for i in range(0,len(indexed_on)):
                        msg += f"    {field_map[dv][i]}\n"
                    raise Exception(msg)

    #print(json.dumps(field_map, indent=4))



def load_manifest(manifest_file):
    """Given a manifest file's path, return the data inside it."""
    identifier = None
    schema = "mcode"
    mapping_path = None
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
    return {
        "identifier": identifier,
        "schema": schema,
        "mapping": mapping_path
    }


def csv_convert(input_path, manifest_file, verbose=False):
    mappings.VERBOSE = verbose

    # read manifest data
    manifest = load_manifest(manifest_file)
    mappings.IDENTIFIER_FIELD = manifest["identifier"]
    if mappings.IDENTIFIER_FIELD is None:
        print("Need to specify what the main identifier column name as 'identifier' in the manifest file")
        return

    # read the schema (from the url specified in the manifest) and generate
    # a scaffold
    schema = MoHSchema(manifest["schema"])
    if schema is None:
        print(f"Did not find an openapi schema at {url}; please check link")
        return

    mapping_template = schema.template

    # read the mapping template (contains the mapping function for each
    # field)
    template_lines = read_mapping_template(manifest["mapping"])

    # # read the raw data
    print("Reading raw data")
    raw_csv_dfs, mappings.OUTPUT_FILE = ingest_raw_data(input_path)
    if not raw_csv_dfs:
        print(f"No ingestable files (csv or xlsx) were found at {input_path}")
        return

    print("Indexing data")
    mappings.INDEXED_DATA = process_data(raw_csv_dfs)
    with open(f"{mappings.OUTPUT_FILE}_indexed.json", 'w') as f:
        json.dump(mappings.INDEXED_DATA, f, indent=4)

    # if verbose flag is set, warn if column name is present in multiple sheets:
    for col in mappings.INDEXED_DATA["columns"]:
        if col != mappings.IDENTIFIER_FIELD and len(mappings.INDEXED_DATA["columns"][col]) > 1:
            mappings._warn(f"Column name {col} present in multiple sheets: {', '.join(mappings.INDEXED_DATA['columns'][col])}")

    # warn if any template lines map the same column to multiple lines:
    scan_template_for_duplicate_mappings(template_lines)

    mapping_scaffold = create_scaffold_from_template(template_lines)

    if mapping_scaffold is None:
        print("Could not create mapping scaffold. Make sure that the manifest specifies a valid csv template.")
        return

    packets = []
    # for each identifier's row, make a packet
    for indiv in mappings.INDEXED_DATA["individuals"]:
        print(f"Creating packet for {indiv}")
        mappings.IDENTIFIER = indiv
        mappings._push_to_stack(None, None, 0)
        packet = map_data_to_scaffold(deepcopy(mapping_scaffold), None, 0)
        if packet is not None:
            packets.extend(packet["DONOR"])
        if mappings._pop_from_stack() is None:
            raise Exception(f"Stack popped too far!\n{mappings.IDENTIFIER_FIELD}: {mappings.IDENTIFIER}")
        if mappings._pop_from_stack() is not None:
            raise Exception(f"Stack not empty\n{mappings.IDENTIFIER_FIELD}: {mappings.IDENTIFIER}\n {mappings.INDEX_STACK}")

    with open(f"{mappings.OUTPUT_FILE}_indexed.json", 'w') as f:
        json.dump(mappings.INDEXED_DATA, f, indent=4)

    result = {
        "openapi_url": schema.openapi_url,
        "donors": packets
    }
    if schema.katsu_sha is not None:
        result["katsu_sha"] = schema.katsu_sha
    with open(f"{mappings.OUTPUT_FILE}_map.json", 'w') as f:    # write to json file for ingestion
        json.dump(result, f, indent=4)

    # add validation data:
    schema.validate_ingest_map(result)
    result["validation_errors"] = schema.validation_failures
    result["statistics"] = schema.statistics
    with open(f"{mappings.OUTPUT_FILE}_map.json", 'w') as f:    # write to json file for ingestion
        json.dump(result, f, indent=4)

    if len(result["validation_errors"]) > 0:
        print("\n\nWARNING: Your data is not valid for the MoHCCN data model! The following errors were found:")
        print("\n".join(result["validation_errors"]))

    return packets


if __name__ == '__main__':
    args = parse_args()
    input_path = args.input
    manifest_file = args.manifest
    csv_convert(input_path, manifest_file, verbose=args.verbose)
