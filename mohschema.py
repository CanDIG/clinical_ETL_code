# mappings and validation based on the mohccn schema

import requests
import yaml
import json
import re
from copy import deepcopy


"""
A class for the representation of a DonorWithClinicalData object in Katsu.
"""

class mohschema:
    schema = {}
    json_schema = None
    template = None
    defs = {}
    schema_name = "DonorWithClinicalData"

    def __init__(self, url, simple=False):
        """Retrieve the schema from the supplied URL, return as dictionary."""
        # TODO: this grabs the schema from a provided URL, which doesn't give us
        # any information about the version. Better to check out a specific katsu
        # version and get schema from local file? (delete repo afterwards)
        resp = requests.get(url)

        # rudimentary test that we have found something that looks like an openapi schema
        # would be better to formally validate
        schema = yaml.safe_load(resp.text)

        if not "openapi" in schema:
            print("Error: does not seem to be an openapi schema")
            schema = None
        self.schema = schema["components"]["schemas"]

        # save off all the component schemas into a "defs" component that can be passed into a jsonschema validation
        defs = set()
        schema_text = resp.text.split("\n")
        for i in range(0, len(schema_text)):
            ref_match = re.match(r"(.*\$ref:) *(.+)$", schema_text[i])
            if ref_match is not None:
                schema_text[i] = schema_text[i].replace("#/components/schemas/", "#/$defs/")
                defs.add(ref_match.group(2).strip('\"').strip("\'").replace("#/components/schemas/", ""))

        openapi_components = yaml.safe_load("\n".join(schema_text))["components"]["schemas"]

        # populate defs for jsonschema
        for d in defs:
            self.defs[d] = openapi_components[d]

        self.json_schema = deepcopy(openapi_components[self.schema_name])
        self.json_schema["$defs"] = self.defs

        # create the template for the DonorWithClinicalData schema
        _, self.template = self.generate_mapping_template(self.generate_schema_array()[self.schema_name])


    def expand_ref(self, ref):
        refName = ref["$ref"].replace("#/components/schemas/", "")
        return self.generate_schema_scaffold(json.loads(json.dumps(self.schema[refName])))


    def generate_schema_scaffold(self, schema_obj):
        result = {}
        if "type" in schema_obj:
            if schema_obj["type"] == "object":
                for prop in schema_obj["properties"]:
                    prop_obj = self.generate_schema_scaffold(schema_obj["properties"][prop])
                    result[prop] = prop_obj
            elif schema_obj["type"] == "array":
                result = [self.generate_schema_scaffold(schema_obj["items"])]
            else:
                result = schema_obj["type"]
        elif "$ref" in schema_obj:
            result = self.expand_ref(schema_obj)
        else:
            result = "unknown"
        return result


    def generate_schema_array(self):
        """
        Generates an array of schema objects and their properties that can
        then be export into a mapping template file.
        """
        schema_array = []
        schema_objects = self.schema

        # find all schemas that have submitter_donor_id in them:
        donor_schemas = []
        for schema in self.schema:
            if "type" in self.schema[schema] and self.schema[schema]["type"] == "object":
                if "submitter_donor_id" in self.schema[schema]["properties"]:
                    donor_schemas.append(schema)
        schema_objs = {}
        for schema in donor_schemas: # each of these high-level schemas is an object
            schema_objs[schema] = self.generate_schema_scaffold(self.schema[schema])

        return schema_objs


    def generate_mapping_template(self, node, node_name="", node_names=None):
        """Create a template for mohschema, for use with the --template flag."""
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
            sc, nn = self.generate_mapping_template(node[0], new_node_name, node_names)
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
                scaffold[prop], node_names = self.generate_mapping_template(node[prop], new_node_name, node_names)
            return scaffold, node_names
        else:
            return str(type(node)), node_names
        return None, node_names

