from copy import deepcopy
import importlib.util
import json
import os
import re
import yaml
from CSVConvert import create_mapping_scaffold, generate_mapping_template
import argparse
from chord_metadata_service.mcode.schemas import MCODE_SCHEMA


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('template', type=str, help="Path to a template mapping file.")
    args = parser.parse_args()
    return args


def map_to_mcodepacket(identifier, node, schema):
    # walk through the provided node of the mcodepacket and fill in the details
    if "str" in str(type(node)):
        return schema
    elif "list" in str(type(node)):
        new_node = []
        for i in range(0,len(node)):
            m = map_to_mcodepacket(identifier, node[i], schema["items"])
            if "list" in str(type(m)):
                new_node = m
            else:
                new_node.append(m)
        return new_node
    elif "dict" in str(type(node)):
        scaffold = {}
        for key in node.keys():
            x = map_to_mcodepacket(identifier, node[key], schema["properties"][key])
            if x is not None:
                scaffold[key] = x
        return scaffold


def main(args):
    template = args.template
    schema, nn = generate_mapping_template(MCODE_SCHEMA)
    print(json.dumps(MCODE_SCHEMA, indent=4))
    if template is not None:
        with open(template, 'r') as f:
            lines = f.readlines()
            mapping_scaffold = create_mapping_scaffold(lines, test=True)
            # print(json.dumps(mapping_scaffold, indent=4))
        if mapping_scaffold is None:
            print("No mapping scaffold was loaded. Either katsu was not found or no schema was specified.")
            return
    else:
        print("A manifest file is required, using the --manifest argument")
        return

    output_file, ext = os.path.splitext(template)

    mcodepackets = [map_to_mcodepacket(0, deepcopy(mapping_scaffold), MCODE_SCHEMA)]

    with open(f"{output_file}_testmap.json", 'w') as f:    # write to json file for ingestion
        json.dump(mcodepackets, f, indent=4)


if __name__ == '__main__':
    main(parse_args())
