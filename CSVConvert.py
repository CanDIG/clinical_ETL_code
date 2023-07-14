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

from mohschema import mohschema


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


def map_data_to_scaffold(node, line):
    """
    Given a particular individual's data, and a node in the schema, return the node with mapped data. Recursive.
    """
    mappings.CURRENT_LINE = line
    verbose_print(f"Mapping line '{mappings.CURRENT_LINE}' for {mappings.IDENTIFIER}")
    curr_id = mappings.peek_at_top_of_stack()
    index_field = curr_id["id"]
    index_value = curr_id["value"]
    identifier = curr_id["indiv"]
    # if we're looking at an array of objects:
    if "dict" in str(type(node)) and "INDEX" in node:
        result = map_indexed_scaffold(node, line)
        if result is not None and len(result) == 0:
            return None
        return result
    if "str" in str(type(node)) and node != "":
        result = eval_mapping(identifier, node, index_field, index_value)
        # if result is not None and len(result) == 0:
        #     return None
        return result
    if "dict" in str(type(node)):
        result = {}
        for key in node.keys():
            dict = map_data_to_scaffold(node[key], f"{line}.{key}")
            if dict is not None:
                result[key] = dict
        if result is not None and len(result) == 0:
            return None
        return result


def map_indexed_scaffold(node, line):
    """
    Given a node that is indexed on some array of values, populate the array with the node's values.
    """
    curr_id = mappings.peek_at_top_of_stack()
    identifier = curr_id["indiv"]
    stack_index_value = curr_id["value"]
    stack_index_field, stack_index_sheets = find_sheets_with_field(curr_id["id"])

    result = []
    index_values = None
    # process the index
    if "INDEX" in node:
        index_method, index_field = parse_mapping_function(node["INDEX"])
        verbose_print(f"  Mapping indexed scaffold for {index_field}")
        if index_field is None:
            return None
        index_field, index_sheets = find_sheets_with_field(index_field[0])
        index_values = eval_mapping(identifier, node["INDEX"], index_field, stack_index_value)
        if index_values is None:
            return None
        if index_field == stack_index_field:
            if stack_index_value in index_values:
                index_values = [stack_index_value]
            else:
                index_values = []
        verbose_print(f"  INDEXED on {index_values} {index_field}")
    else:
        raise Exception(f"An indexed_on notation is required for {line}")

    if node["NODES"] is None:
        # there isn't any more depth to this, so just return the values
        return index_values
    verbose_print(f"Processing over index values {index_values}")
    for i in index_values:
        verbose_print(f"Applying {i} to {line}")
        mappings.push_to_stack(f'"{index_sheets[0]}".{index_field}', i, identifier)
        sub_res = map_data_to_scaffold(node["NODES"], f"{line}.INDEX")
        if sub_res is not None:
            result.append(map_data_to_scaffold(node["NODES"], f"{line}.INDEX"))
        mappings.pop_from_stack()
    if len(result) == 0:
        return None
    return result


def find_sheets_with_field(param):
    """
    For a named parameter, find all of the sheets that have this parameter on them.
    If the parameter specifies a sheet, return just that sheet and the parameter's base name.
    Returns None, None if the parameter is not found.
    """
    if param is None:
        return None, None
    param = param.strip()
    sheet_match = re.match(r"(.+?)\.(.+)", param)
    if sheet_match is not None:
        # this param is a specific item on a specific sheet:
        param = sheet_match.group(2)
        sheet = sheet_match.group(1).replace('"', '').replace("'", "")
        # is this param a column?
        if param in mappings.INDEXED_DATA["columns"]:
            if sheet in mappings.INDEXED_DATA["columns"][param]:
                return param, [sheet]
    else:
        if param in mappings.INDEXED_DATA["columns"]:
            return param, mappings.INDEXED_DATA["columns"][param]
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
    return method, parameters


def populate_data_for_params(identifier, index_field, index_value, params):
    """
    Given a list of params, return a dictionary of the
    values for each parameter.
    If index_field is not None, create an INDEX key that lists all the possible values that could use
    """
    curr_id = mappings.peek_at_top_of_stack()
    stack_index_field, stack_index_sheets = find_sheets_with_field(curr_id["id"])
    stack_index_value = curr_id["value"]

    data_values = {}
    param_names = []

    # verbose_print(f"populating with {identifier} {index_field} {index_value} {params}")
    for param in params:
        param, sheets = find_sheets_with_field(param)
        if param is None:
            return None, None
        if sheets is None or len(sheets) == 0:
            verbose_print(f"  WARNING: parameter {param} is not present in the input data")
        else:
            verbose_print(f"  populating data for {param} in {sheets}")
            param_names.append(param)
            for sheet in sheets:
                if param not in data_values:
                    data_values[param] = {}
                # for each of these sheets, add this identifier's contents as a key and array:
                if identifier in mappings.INDEXED_DATA["data"][sheet]:
                    if sheet not in data_values[param]:
                        data_values[param][sheet] = mappings.INDEXED_DATA["data"][sheet][identifier][param]
                    # if index_field is not None, add only the indexed data where the index_field's value is identifier
                    if index_field is not None and index_value is not None:
                        index_field, index_sheets = find_sheets_with_field(index_field)
                        verbose_print(f"    checking if {index_field} == {stack_index_field} and {index_value} == {stack_index_value}")
                        # if index_field is the same as stack_index_field, then index_value should equal stack's value
                        if index_field == stack_index_field and index_value == stack_index_value:
                            verbose_print(f"    Is {index_value} in {sheet}>{identifier}>{index_field}? {mappings.INDEXED_DATA['data'][index_sheets[0]][identifier][index_field]}")
                            if index_value in mappings.INDEXED_DATA["data"][index_sheets[0]][identifier][index_field]:
                                verbose_print(f"    yes, data_values[{index_sheets[0]}] = {mappings.INDEXED_DATA['data'][index_sheets[0]][identifier]}")
                                # if indexed_data["data"][sheet][identifier][index_field] has more than one value, find the index for index_value and use just that one
                                data_values[param][sheet] = {}
                                i = mappings.INDEXED_DATA["data"][index_sheets[0]][identifier][index_field].index(index_value)
                                if len(mappings.INDEXED_DATA["data"][sheet][identifier][param]) >= i:
                                    data_values[param][sheet] = [mappings.INDEXED_DATA["data"][sheet][identifier][param][i]]
                            else:
                                data_values[param].pop(sheet)
                else:
                    verbose_print(f"  WARNING: {identifier} not on sheet {sheet}")
                    data_values[param][sheet] = []
    verbose_print(f"  populated {data_values} {param_names}")
    return data_values, param_names

def eval_mapping(identifier, node_name, index_field, index_value):
    """
    Given the identifier field, the data, and a particular schema node, evaluate
    the mapping using the provider method and return the final JSON for the node
    in the schema.
    If index_value is not None, it is an index into an object that is part of an array.
    """
    verbose_print(f"  Evaluating {identifier}: {node_name} (indexed on {index_field}, {index_value})")
    if "mappings" not in mappings.MODULES:
        mappings.MODULES["mappings"] = importlib.import_module("mappings")
    modulename = "mappings"

    method, parameters = parse_mapping_function(node_name)
    if parameters is None:
        # by default, map using the node name as a parameter
        parameters = [node_name]
    data_values, parameters = populate_data_for_params(identifier, index_field, index_value, parameters)
    if parameters is None or (len(parameters) > 0 and parameters[0] == "NONE"):
        return None
    if method is not None:
        # is the function something in a dynamically-loaded module?
        subfunc_match = re.match(r"(.+)\.(.+)", method)
        if subfunc_match is not None:
            modulename = subfunc_match.group(1)
            method = subfunc_match.group(2)
    # else:
    #     method = "single_val"
    #     verbose_print(f"  Defaulting to single_val({parameters})")
    verbose_print(f"  Using method {modulename}.{method}({parameters}) with {data_values}")
    try:
        if len(data_values.keys()) > 0:
            module = mappings.MODULES[modulename]
            return eval(f'module.{method}({data_values})')
    except mappings.MappingError as e:
        print(f"Error evaluating {method}")
        raise e


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


def process_data(raw_csv_dfs):
    """Takes a set of raw dataframes with a common identifier and merges into a  JSON data structure."""
    final_merged = {}
    cols_index = {}
    individuals = []
    identifier = mappings.IDENTIFIER_FIELD

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
            merged_dict[i][identifier] = [merged_dict[i][identifier].pop()]

        # Now we can clean up the dicts: index them by identifier instead of int
        indexed_merged_dict = {}
        for i in range(0, len(merged_dict.keys())):
            indiv = merged_dict[i][identifier][0]
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
        else:
            print(f"WARNING: Line '{mapped_key}' not in schema")
    return scaffold_template


def main(args):
    input_path = args.input
    manifest_file = args.manifest
    mappings.VERBOSE = args.verbose

    # read manifest data
    manifest = load_manifest(manifest_file)
    mappings.IDENTIFIER_FIELD = manifest["identifier"]
    indexed = manifest["indexed"]
    if mappings.IDENTIFIER_FIELD is None:
        print("Need to specify what the main identifier column name as 'identifier' in the manifest file")
        return

    # read the schema (from the url specified in the manifest) and generate
    # a scaffold
    schema = mohschema(manifest["schema"])
    if schema is None:
        print(f"Did not find an openapi schema at {url}; please check link")
        return

    mapping_template = schema.template

    # read the mapping template (contains the mapping function for each
    # field)
    template_lines = read_mapping_template(manifest["mapping"])

    # # read the raw data
    print("Reading raw data")
    raw_csv_dfs, output_file = ingest_raw_data(input_path, indexed)
    if not raw_csv_dfs:
        print(f"No ingestable files (csv or xlsx) were found at {input_path}")
        return

    print("Indexing data")
    mappings.INDEXED_DATA = process_data(raw_csv_dfs)
    with open(f"{output_file}_indexed.json", 'w') as f:
        json.dump(mappings.INDEXED_DATA, f, indent=4)

    # if verbose flag is set, warn if column name is present in multiple sheets:
    for col in mappings.INDEXED_DATA["columns"]:
        if col != mappings.IDENTIFIER_FIELD and len(mappings.INDEXED_DATA["columns"][col]) > 1:
            mappings.warn(f"Column name {col} present in multiple sheets: {', '.join(mappings.INDEXED_DATA['columns'][col])}")

    ## Replace the lines in the original template with any matching lines in template_lines
    if not args.test:
        interpolate_mapping_into_scaffold(template_lines, mapping_template)
        mapping_scaffold = create_scaffold_from_template(mapping_template)
    else:
        mapping_scaffold = create_scaffold_from_template(template_lines)

    if mapping_scaffold is None:
        print("Could not create mapping scaffold. Make sure that the manifest specifies a valid csv template.")
        return

    packets = []
    # for each identifier's row, make a packet
    for indiv in mappings.INDEXED_DATA["individuals"]:
        print(f"Creating packet for {indiv}")
        mappings.IDENTIFIER = indiv
        mappings.push_to_stack(None, None, indiv)
        packets.append(map_data_to_scaffold(deepcopy(mapping_scaffold), "DONOR"))
        if mappings.pop_from_stack() is None:
            raise Exception(f"Stack popped too far!\n{mappings.IDENTIFIER_FIELD}: {mappings.IDENTIFIER}")
        if mappings.pop_from_stack() is not None:
            raise Exception(f"Stack not empty\n{mappings.IDENTIFIER_FIELD}: {mappings.IDENTIFIER}\n {mappings.INDEX_STACK}")

    with open(f"{output_file}_indexed.json", 'w') as f:
        json.dump(mappings.INDEXED_DATA, f, indent=4)

    with open(f"{output_file}_map.json", 'w') as f:    # write to json file for ingestion
        json.dump(packets, f, indent=4)


if __name__ == '__main__':
    main(parse_args())
