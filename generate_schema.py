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
from moh_mappings import mohschema


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, help="URL to openAPI schema file (raw github link)", required=True)
    parser.add_argument('--out', type=str, help="name of output file; csv extension will be added. Default is template", default="template")
    args = parser.parse_args()
    return args


def generate_mapping_template(node, node_name="", node_names=None):
    """Create a template for mcodepacket, for use with the --template flag."""
    if node_names is None:
        node_names = []
    if node_name != "":
        # check to see if the last node_name is a header for this node_name:
        if len(node_names) > 0:
            x = node_names.pop()
            x_match = re.match(r"(.+?)\**,.*", x)
            if x_match is not None:
                if x_match.group(1) in node_name:
                    node_names.append(f"##{x}")
                else:
                    node_names.append(x)
            else:
                node_names.append(x)
        if "description" in node:
            node_names.append(f"{node_name},\"##{node['description']}\"")
        else:
            node_names.append(f"{node_name},")
    if "type" in node:
        if node["type"] == "string":
            return "string", node_names
        elif node["type"] == "array":
            new_node_name = ".".join((node_name, "0"))
            sc, nn = generate_mapping_template(node["items"], new_node_name, node_names)
            return [sc], nn
        elif node["type"] in ["number", "integer"]:
            return 0, node_names
        elif node["type"] == "boolean":
            return True, node_names
        elif node["type"] == "object":
            scaffold = {}
            if "$id" in node:
                scaffold["$id"] = node["$id"]
            if len(node_names) > 0:
                # if this is an ontology_class_schema, we'll update this data post-mapping
                if "$id" in node and (node["$id"] == "katsu:common:ontology_class"
                                      or node["$id"] == "katsu:mcode:complex_ontology"):
                    # add a + to the name of the node to denote that this needs to be looked up in an ontology
                    name = node_names.pop()
                    name_match = re.match(r"(.+?),(.+)", name)
                    if name_match is not None:
                        name = f"{name_match.group(1)}+,{name_match.group(2)}"
                    node_names.append(name)
                    return node["$id"], node_names
            if "properties" in node:
                for prop in node["properties"]:
                    if node_name == "":
                        new_node_name = prop
                    else:
                        new_node_name = ".".join((node_name, prop))
                    if "required" in node and prop in node["required"]:
                        new_node_name += "*"
                    scaffold[prop], node_names = generate_mapping_template(node["properties"][prop], new_node_name, node_names)
            return scaffold, node_names
    else:
        return {}, node_names
    return None, node_names

def main(args):
 
    url = args.url
    schema = mohschema(url)
    if schema is None:
        print("Did not find an openapi schema at {}; please check link".format(url))
        return
    schema_array = schema.generate_schema_array()
    
    outputfile = "{}.csv".format(args.out)
    print(f"Outputting schema template to {outputfile}")
    with open(outputfile,'w') as f:
        f.write("# Schema generated from {}\n".format(url))
        f.write("# mohschema.fieldname,mapping_function\n")
        f.writelines(schema_array)
    

    # metadata = ""
    
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
    # sc, node_names = generate_mapping_template(schema)
        
    # with open(f"{template}.csv", 'w') as f:  # write to csv file for mapping
    #     f.write(metadata)
    #     f.write("## mcodepacket element, description (overwrite with mapped element)\n")
    #     f.write("## (.0 is an array element) (* is required) (+ denotes ontology term),\n")
    #     for nn in node_names:
    #         f.write(f"{nn}\n")
    return

if __name__ == '__main__':
    main(parse_args())

