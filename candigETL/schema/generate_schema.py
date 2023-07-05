#!/usr/bin/env python
# coding: utf-8

import argparse
from mohschema import mohschema


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, help="URL to openAPI schema file (raw github link)", default="https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/docs/schema.yml")
    parser.add_argument('--out', type=str, help="name of output file; csv extension will be added. Default is template", default="template")
    args = parser.parse_args()
    return args


def main(args):
    url = args.url
    schema = mohschema(url)
    if schema is None:
        print("Did not find an openapi schema at {}; please check link".format(url))
        return

    outputfile = "{}.csv".format(args.out)

    metadata = ""

    node_names = schema.template

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

