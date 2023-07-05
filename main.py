import json
import argparse
from copy import deepcopy

from candigETL.schema.mohschema import mohschema
from candigETL.convert.CSVConvert import *

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required = True, help="Path to either an xlsx file or a directory of csv files for ingest")
    # parser.add_argument('--api_key', type=str, help="BioPortal API key found in BioPortal personal account settings")
    # parser.add_argument('--email', type=str, help="Contact email to access NCBI clinvar API. Required by Entrez")
    #parser.add_argument('--schema', type=str, help="Schema to use for template; default is mCodePacket")
    parser.add_argument('--manifest', type=str, required = True, help="Path to a manifest file describing the mapping."
                                                                  " See README for more information")
    parser.add_argument('--verbose', '--v', action="store_true", help="Print extra information")
    parser.add_argument('--test', '--t', type=bool)
    args = parser.parse_args()
    return args

args = parse_args()

if __name__ == '__main__':
    input_path = args.input
    manifest_file = args.manifest
    mappings.VERBOSE = args.verbose

    # read manifest data
    manifest = load_manifest(manifest_file)
    mappings.IDENTIFIER_FIELD = manifest["identifier"]
    indexed = manifest["indexed"]
    if mappings.IDENTIFIER_FIELD is None:
        print("Need to specify what the main identifier column name as 'identifier' in the manifest file")
        exit()

    # read the schema (from the url specified in the manifest) and generate
    # a scaffold
    schema = mohschema(manifest["schema"])
    if schema is None:
        print(f"Did not find an openapi schema at {url}; please check link")
        exit()

    mapping_template = schema.template

    # read the mapping template (contains the mapping function for each
    # field)
    template_lines = read_mapping_template(manifest["mapping"])

    ## Replace the lines in the original template with any matching lines in template_lines
    if not args.test:
        interpolate_mapping_into_scaffold(template_lines, mapping_template)
        mapping_scaffold = create_scaffold_from_template(mapping_template)
    else:
        mapping_scaffold = create_scaffold_from_template(template_lines)

    if mapping_scaffold is None:
        print("Could not create mapping scaffold. Make sure that the manifest specifies a valid csv template.")
        exit()

    # # read the raw data
    print("Reading raw data")
    raw_csv_dfs, output_file = ingest_raw_data(input_path, indexed)
    if not raw_csv_dfs:
        print(f"No ingestable files (csv or xlsx) were found at {input_path}")
        exit()

    print("Indexing data")
    mappings.INDEXED_DATA = process_data(raw_csv_dfs, mappings.IDENTIFIER_FIELD)
    with open(f"{output_file}_indexed.json", 'w') as f:
        json.dump(mappings.INDEXED_DATA, f, indent=4)

    # if verbose flag is set, warn if column name is present in multiple sheets:
    for col in mappings.INDEXED_DATA["columns"]:
        if col != mappings.IDENTIFIER_FIELD and len(mappings.INDEXED_DATA["columns"][col]) > 1:
            mappings.warn(
                f"Column name {col} present in multiple sheets: {', '.join(mappings.INDEXED_DATA['columns'][col])}")

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
            raise Exception(
                f"Stack not empty\n{mappings.IDENTIFIER_FIELD}: {mappings.IDENTIFIER}\n {mappings.INDEX_STACK}")

    with open(f"{output_file}_indexed.json", 'w') as f:
        json.dump(mappings.INDEXED_DATA, f, indent=4)

    with open(f"{output_file}_map.json", 'w') as f:  # write to json file for ingestion
        json.dump(packets, f, indent=4)