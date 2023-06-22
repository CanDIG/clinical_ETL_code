#!/usr/bin/env python
# coding: utf-8

from copy import deepcopy
import importlib.util
from importlib.metadata import files, version
import json
import mappings
import os
import pandas
import sys
import argparse
from mohschema import mohschema
import re


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, help="URL to openAPI schema file (raw github link)", default="https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/docs/schema.yml")
    parser.add_argument('--out', type=str, help="name of output file; csv extension will be added. Default is template", default="template")
    args = parser.parse_args()
    return args


def generate_mapping_template(node, node_name="", node_names=None):
    """Create a template for mcodepacket, for use with the --template flag."""
    if node_names is None:
        node_names = []
    if node_name != "" and not node_name.endswith(".id"):
        # check to see if the last node_name is a header for this node_name:
        if len(node_names) > 0:
            x = node_names.pop()
            x_match = re.match(r"(.+?)\**,.*", x)
            if x_match is not None:
                if x_match.group(1) not in node_name:
                    node_names.append(x)
                elif x.endswith(".INDEX,"):
                    node_names.append(x)
            else:
                node_names.append(x)
        if "description" in node:
            node_names.append(f"{node_name},\"##{node['description']}\"")
        else:
            node_names.append(f"{node_name},")
    if "str" in str(type(node)):
        return "string", node_names
    elif "list" in str(type(node)):
        new_node_name = ".".join((node_name, "INDEX"))
        sc, nn = generate_mapping_template(node[0], new_node_name, node_names)
        return [sc], nn
    elif "number" in str(type(node)) or "integer" in str(type(node)):
        return 0, node_names
    elif "boolean" in str(type(node)):
        return True, node_names
    elif "dict" in str(type(node)):
        scaffold = {}
        for prop in node.keys():
            if node_name == "":
                new_node_name = prop
            else:
                new_node_name = ".".join((node_name, prop))
            scaffold[prop], node_names = generate_mapping_template(node[prop], new_node_name, node_names)
        return scaffold, node_names
    else:
        return str(type(node)), node_names
    return None, node_names

def main(args):
    url = args.url
    schema = mohschema(url)
    if schema is None:
        print("Did not find an openapi schema at {}; please check link".format(url))
        return
    schema_array = schema.generate_schema_array()

    outputfile = "{}.csv".format(args.out)

    metadata = ""

    # if schema is None:
    #     schema = MCODE_SCHEMA
    #     # get metadata about version of MCODE_SCHEMA used:
    #     metadata += "## schema based on version " + version('katsu') + ",\n"
    #     direct_url = [p for p in files('katsu') if 'direct_url.json' in str(p)]
    #     if len(direct_url) > 0:
    #         d = json.loads(direct_url[0].read_text())
    #         metadata += f"## directly checked out from {d['url']}, commit {d['vcs_info']['commit_id']}\n"
    # if schema == "candigv1":
    #     schema = candigv1_schema
    sc, node_names = generate_mapping_template(schema_array["DonorWithClinicalData"])

    with open(outputfile, 'w') as f:  # write to csv file for mapping
        f.write(metadata)
        f.write("## mohpacket element, description (overwrite with mapped element)\n")
        # f.write("## (.INDEX is an array element) (* is required) (+ denotes ontology term),\n")
        for nn in node_names:
            f.write(f"{nn}\n")
    print(f"Template written to {outputfile}")
    return

if __name__ == '__main__':
    main(parse_args())

