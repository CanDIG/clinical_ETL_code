# mappings and validation based on the mohccn schema

import requests
import yaml
import json
import re
import mappings
from copy import deepcopy


"""
The top-level keys of the schema are:
    [openapi, # required def line
    info, # metadata
    paths, # API paths
    components # schema parts, this is the core info for ETL
    ]
"""

class mohschema:
    schema = {}
    skipped_schemas = [
        "Patched","Paginated","Discovery","DonorWithClinicalData","Request","Nested","data_ingest","moh","Enum"
        ]

    def __init__(self,url, simple=False):
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
                # print(ref_match.group(2).strip('\"').strip("\'").replace("#/components/schemas/", ""))
                defs.add(ref_match.group(2).strip('\"').strip("\'").replace("#/components/schemas/", ""))

        self.json_schema = yaml.safe_load("\n".join(schema_text))["components"]["schemas"]
        self.defs = {}
        for d in defs:
            self.defs[d] = self.json_schema[d]


    def get_json_schema(self, schema_name):
        result = deepcopy(self.json_schema[schema_name])
        result["$defs"] = self.defs
        return result



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
        """Generates an array of schema objects and their properties that can
        then be export into a mapping template file. Same code as generate_scaffold
        but returns an array instead of a dict. """
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


    def generate_scaffold(self):
        """Generate a simplied version of the schema with only the schema
        objects that are not in skipped_schemas. Similar code as
        generate_schema_array but returns a dict instead of an array."""
        scaffold = {}
        schema_objects = self.schema
        for s in schema_objects.keys():
            for test in self.skipped_schemas:
                if re.search(test,s):
                    break
            else:
                #properties = schema_objects[s]["properties"]
                #scaffold[s] = properties
                scaffold[s] = schema_objects[s]
        return scaffold

    def get_schema_data(self, schema_name):
        """Given the name of a schema object, return the type"""
        try:
            return self.schema[schema_name]
        except KeyError:
            raise KeyError(f"No schema oject {schema_name} in schema")

    def get_schema_type(self, schema_name):
        """Given the name of a schema object, return the type"""

        # next two code lines are how this should work, once we have the info in
        # the schema, although might need modification depending on final structure
        #schema_data = self.get_schema_data(schema_name)
        #return schema_data['type']

        # but in the meantime, as a hack, we hard code everything
        if schema_name == "Donor":
            return "not_an_array"
        else:
            return "array"

    def get_property_type(self,schema_name,node):
        """Given the name of a schema object, and a property of that node,
        return the type"""
        schema_data = self.get_schema_data(schema_name)
        try:
            node_data = schema_data['properties'][node]
            return node_data['type']
        except KeyError:
            raise KeyError(f"No property {node} for {schema_name}")



