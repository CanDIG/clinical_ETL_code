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
import re


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, help="URL to openAPI schema file (raw github link)",
                        default="https://raw.githubusercontent.com/CanDIG/katsu/refs/heads/features/model_4/chord_metadata_service/mohpackets/docs/schemas/schema.json")
    parser.add_argument('--schema', type=str, help="Name of schema class", default="MoHSchemaV4")
    parser.add_argument('--out', type=str,
                        help="name of output file; csv extension will be added. Default is moh_template",
                        default="moh_template")
    args = parser.parse_args()
    return args


def main(args):
    url = args.url
    schema_name = args.schema
    schema_class = schema_name.lower()
    mod = importlib.import_module(schema_class)
    schema = eval(f'mod.{schema_name}(url)')
    if schema is None:
        print("Did not find an openapi schema at {}; please check link".format(url))
        return

    outputfile = "{}.csv".format(args.out)

    metadata = f"## Schema generated from {url}\n"
    if schema.katsu_sha is not None:
        metadata += f"## Based on repo commit sha \"{schema.katsu_sha}\"\n"

    with open(outputfile, 'w') as f:  # write to csv file for mapping
        f.write(metadata)
        f.write("## Items are comma separated: element, mapping method\n")
        # f.write("## (.INDEX is an array element) (* is required) (+ denotes ontology term),\n")
        # A schema may define more than one top-level root (e.g. v4 donors + programs);
        # write each root's template lines, in declared order.
        for root_key in schema._root_order:
            root = schema.roots[root_key]
            f.write(f"## {root['base_name']} ({root['schema_name']})\n")
            for nn in root["template"]:
                f.write(f"{nn}\n")
    print(f"Template written to {outputfile}")
    return

if __name__ == '__main__':
    main(parse_args())

