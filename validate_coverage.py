import argparse
import json
import jsonschema
import os
import re
import CSVConvert
import mappings
from copy import deepcopy
from mohschema import mohschema
from jsoncomparison import Compare


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=str, help="Path to a manifest file describing the mapping.")
    parser.add_argument('--json', type=str, help="JSON file generated by CSVConvert.")
    parser.add_argument('--input', type=str, help="Directory to the raw clinical data used for creating the JSON file.")
    parser.add_argument('--verbose', '--v', action="store_true", help="Print extra information")
    args = parser.parse_args()
    return args


def clean_compare(compare, expected, actual):
    """Takes in a Compare object and the original compared JSONs and cleans up the formatting."""
    new_compare = {}
    for key in compare:
        if "_message" in compare[key]:
            if "Values not equal." not in compare[key]["_message"]:
                new_compare[key] = compare[key]
                if "Key does not exists." in compare[key]["_message"]:
                    new_compare.pop(key)
        elif "_content" in compare[key]:
            check = clean_compare(compare[key]["_content"][0], expected[key][0], actual[key][0])
            if len(check) > 0:
                new_compare[key] = check
        else:
            check = clean_compare(compare[key], expected[key], actual[key])
            if len(check) > 0:
                new_compare[key] = check
    return new_compare


def flatten_mapping(node, node_name="", node_names=None):
    """Converts a JSON node into a flattened list of items."""
    if node_names is None:
        node_names = []
    if node_name != "":
        node_names.append(node_name)
    if "list" in str(type(node)) and len(node) > 0:
        new_node_name = ".".join((node_name, "0"))
        sc, nn = flatten_mapping(node[0], new_node_name, node_names)
        return [sc], nn
    elif "dict" in str(type(node)):
        scaffold = {}
        for prop in node.keys():
            if node_name == "":
                new_node_name = prop
            else:
                new_node_name = ".".join((node_name, prop))
            scaffold[prop], node_names = flatten_mapping(node[prop], new_node_name, node_names)
        return scaffold, node_names
    else:
        return "string", node_names
    return None, node_names


def check_completeness(schema):
    # expected mapping
    expected_flattened = schema.template
    expected_scaffold = CSVConvert.create_scaffold_from_template(expected_flattened, test=True)
    expected = CSVConvert.map_data_to_scaffold(deepcopy(expected_scaffold), "DONOR")
    print(expected)
    return
    # actual mapping
    template_lines = CSVConvert.read_mapping_template(manifest["mapping"])
    actual_flattened = deepcopy(expected_flattened)
    CSVConvert.interpolate_mapping_into_scaffold(template_lines, actual_flattened)
    mapping_scaffold = CSVConvert.create_scaffold_from_template(actual_flattened)
    actual = CSVConvert.map_data_to_scaffold(deepcopy(mapping_scaffold), "DONOR")

    print(expected, actual)
    # compare the actual mapping and report any mismatches
    compare = clean_compare(Compare().check(expected, actual), expected, actual)
    if len(compare.keys()) > 0:
        print("\n\nSome items in the mapping do not match the schema:")
        print(json.dumps(compare, indent=4))

    # quantify mapping coverage of all data sheets
    all_sheets = list(indexed_data["columns"][identifier]) # identifier is in all sheets

    return
    maps = set()
    for line in mapping_lines:
        value, elems = parse_mapping_function(line)
        method, mapping = parse_mapping_function(identifier, indexed_data, value)
        if mapping is not None:
            for col in maps.keys():
                maps.add(json.dumps({col: list(mapping[col].keys())}))
    vals = []
    for mapping in maps:
        mapping = json.loads(mapping)
        column = list(mapping.keys())[0]
        if column != identifier:
            vals.append({"column": column, "sheets": mapping[column]})
    vals_by_sheets = sorted(vals, key=(lambda x: len(x["sheets"])))

    accessed_sheets = {}
    for val in vals_by_sheets:
        sheet = val["sheets"].pop()
        if len(val["sheets"]) == 0: # only one value, so we need it for sure:
            if sheet not in accessed_sheets:
                accessed_sheets[sheet] = [val['column']]
            elif val['column'] not in accessed_sheets[sheet]:
                accessed_sheets[sheet].append(val['column'])
        elif len(val["sheets"]) > 0: # look for this column name in existing sheets
            while len(val["sheets"]) > 0:
                if sheet in accessed_sheets:
                    break
                sheet = val["sheets"].pop()
            if len(val["sheets"]) == 0: # it's not in any of those, so add the col to the last sheet seen
                accessed_sheets[sheet] = [val['column']]
    # print(json.dumps(accessed_sheets, indent=4))
    print("\n\nMapping coverage of the clinical data provided:")
    print("Sheet\tColumns used\tTotal columns (not including identifier)")
    for sheet in all_sheets:
        subject = list(indexed_data["data"][sheet].keys())[0]
        data = list(indexed_data["data"][sheet][subject].keys())
        data.remove(identifier)
        cols_used = 0
        if sheet in accessed_sheets:
            if "index" in accessed_sheets[sheet]: # don't count index; it's not a real column
                accessed_sheets[sheet].remove("index")
            cols_used = len(accessed_sheets[sheet])
        print(f"{sheet}\t{cols_used}\t{len(data)}")

    # look for missing fields from the schema
    # create an actual mapping of all items used for any individual
    items_used = []
    for key in indexed_data["individuals"]:
        sc, actual_flattened = flatten_mapping(map_row_to_mcodepacket(key, indexed_data, scaffold))
        for i in range(0, len(actual_flattened)):
            curr_item = actual_flattened[i]
            if curr_item not in items_used:
                # if this is not the first item, file it in the spot it goes in the order:
                if i > 0:
                    prev_item = actual_flattened[i-1]
                    prev_index = items_used.index(prev_item)
                    items_used.insert(prev_index+1, curr_item)
                else:
                    items_used.insert(0, curr_item)

    # print the actual items used:
    print("Items successfully mapped onto the schema:")
    print("\n".join(map(lambda x: x.replace('"',"").replace("'",""), items_used)))

    missing = []

    print("\n\nMapping is missing the following items from the schema:")
    actual = items_used.pop(0)
    while len(items_used) > 0:
        if len(expected_flattened) == 0:
            break
        expected = expected_flattened.pop(0)

        # skip any extra_properties, because these are definitely not needed
        while "extra_properties" in expected and len(expected_flattened) > 0:
            expected = expected_flattened.pop(0)
        if len(expected_flattened) == 0:
            break

        while "extra_properties" in actual and len(items_used) > 0:
            actual = items_used.pop(0)
        if len(items_used) == 0:
            break

        patt = re.compile(f"^(##)*{actual}([\*\+])*,.*")
        expected_match = re.match(patt, expected)
        if expected_match is not None:
            # print(f"++{actual}, {expected}")
            if expected_match.group(2) == "+":
                # need to pop the next two actuals
                actual = items_used.pop(0)
                actual = items_used.pop(0)
            if len(items_used) > 0:
                actual = items_used.pop(0)
            else:
                break
        else:
            # print(f"--{actual}, {expected}")
            comment_match = re.match(r"^(##)*(.*?)(,.*)", expected)
            if comment_match is not None:
                if comment_match.group(1) is None:
                    missing.append(comment_match.group(2))
    print("\n".join(missing))


def main(args):
    map_json_file = args.json
    manifest = args.manifest
    input_path = args.input

    if args.verbose:
        mappings.VERBOSE = True

    # if manifest is provided, we should create a manifest scaffold
    if manifest is not None:
        manifest = CSVConvert.load_manifest(manifest)
        mappings.IDENTIFIER_FIELD = manifest["identifier"]
        schema = manifest["schema"]
        indexed = manifest["indexed"]
        mapping_lines = manifest["mapping"]
        if mappings.IDENTIFIER_FIELD is None:
            print("Need to specify what the main identifier column name is in the manifest file")
            return
    else:
        print("A manifest file is required, using the --manifest argument")
        return

    map_json = None
    if map_json_file is not None and os.path.isfile(map_json_file):
            with open(map_json_file) as fp:
                map_json = json.load(fp)
    else:
        print("A JSON file, generated by CSVConvert.py, is required, using the --input argument")
        return

    # read the schema (from the url specified in the manifest) and generate
        # a scaffold
    schema = mohschema(manifest["schema"])
    if schema is None:
        print(f"Did not find an openapi schema at {url}; please check link")
        return

    # if --input was specified, we can check data frame completeness coverage:
    if input_path is not None:
        raw_csv_dfs, output_file = CSVConvert.ingest_raw_data(input_path, indexed)
        if not raw_csv_dfs:
            print(f"No ingestable files (csv or xlsx) were found at {input_path}")
            return
        mappings.INDEXED_DATA = CSVConvert.process_data(raw_csv_dfs)
        mappings.IDENTIFIER = mappings.INDEXED_DATA["individuals"][0]
        mappings.push_to_stack(None, None, mappings.IDENTIFIER)
        print("Comparing input data and mapped data for completeness of coverage...")
        check_completeness(schema)

    # validate with jsonschema:
    print("Validating the mapped schema...")
    components = schema.json_schema
    result = jsonschema.validate(map_json[0], components)
    print("Mapping is valid!")
    return


if __name__ == '__main__':
    main(parse_args())
