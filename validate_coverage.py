import argparse
import json
import re
from CSVConvert import ingest_raw_data, process_data, load_manifest, translate_mapping, process_mapping, generate_mapping_template, map_row_to_mcodepacket, create_mapping_scaffold
from create_test_mapping import map_to_mcodepacket
from chord_metadata_service.mcode.schemas import MCODE_SCHEMA
from copy import deepcopy
from jsoncomparison import Compare


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapping', '--manifest', type=str, help="Path to a manifest file describing the mapping.")
    parser.add_argument('--input', type=str, help="Clinical data for mapping.")
    args = parser.parse_args()
    return args


def clean_compare(compare, expected, actual):
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
    if node_names is None:
        node_names = []
    if node_name != "":
        node_names.append(node_name)
    if "list" in str(type(node)):
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


def main(args):
    input_path = args.input
    mapping = args.mapping
    
    # if mapping is provided, we should create a mapping scaffold
    if mapping is not None:
        manifest = load_manifest(mapping)
        identifier = manifest["identifier"]
        schema = manifest["schema"]
        scaffold = manifest["scaffold"]
        indexed = manifest["indexed"]
        mapping = manifest["mapping"]
        if identifier is None:
            print("Need to specify what the main identifier column name is in the manifest file")
            return
        if scaffold is None:
            print("No mapping scaffold was loaded. Either katsu was not found or no schema was specified.")
            return
    else:
        print("A manifest file is required, using the --manifest argument")
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

    # actual mapping
    key = indexed_data["individuals"][0]
    actual = map_row_to_mcodepacket(key, indexed_data, scaffold)

    # test mapping
    schema, expected_flattened = generate_mapping_template(MCODE_SCHEMA)
    expected = map_to_mcodepacket(key, create_mapping_scaffold(expected_flattened, test=True), MCODE_SCHEMA)

    # compare the actual mapping and report any mismatches
    compare = clean_compare(Compare().check(expected, actual), expected, actual)
    if len(compare.keys()) > 0:
        print("\n\nSome items in the mapping do not match the schema:")
        print(json.dumps(compare, indent=4))

    # quantify mapping coverage of all data sheets
    all_sheets = list(indexed_data["columns"][identifier]) # identifier is in all sheets

    mappings = set()
    for line in mapping:
        value, elems = process_mapping(line)
        method, mapping = translate_mapping(identifier, indexed_data, value)
        if mapping is not None:
            for col in mapping.keys():
                mappings.add(json.dumps({col: list(mapping[col].keys())}))
    vals = []
    for mapping in mappings:
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


if __name__ == '__main__':
    main(parse_args())
