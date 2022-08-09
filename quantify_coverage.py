import argparse
import json
from CSVConvert import ingest_raw_data, process_data, load_manifest, translate_mapping, process_mapping


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapping', '--manifest', type=str, help="Path to a manifest file describing the mapping.")
    parser.add_argument('--input', type=str, help="Clinical data for mapping.")
    args = parser.parse_args()
    return args


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
                accessed_sheets[sheet].append(val['column'])
    # print(json.dumps(accessed_sheets, indent=4))
    
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
        print(f"{sheet}\t{cols_used}\t{len(data)-1}")

if __name__ == '__main__':
    main(parse_args())
