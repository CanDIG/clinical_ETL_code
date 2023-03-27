# mappings and validation based on the mohccn schema

import requests 
import yaml
import re
import mappings
    
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
    #skipped_schemas = []
    skipped_schemas = [
        "Patched","Paginated","Discovery","DonorWithClinicalData","Request","Nested","data_ingest","moh","Enum"
        ]

    def __init__(self,url, simple=False):
        """Retrieve the schema from the supplied URL, return as dictionary."""
        resp = requests.get(url)
        schema = yaml.safe_load(resp.text)
        # rudimentary test that we have found something that looks like an openapi schema
        # would be better to formally validate
        if not "openapi" in schema:
            print("Error: does not seem to be an openapi schema")
            schema = None
        schema.pop("paths") # we don't need the path info
        self.schema = schema

    def generate_schema_array(self):
        """Generates an array of schema objects and their properties that can
        then be export into a mapping template file. Same code as generate_scaffold
        but returns an array instead of a dict. """
        schema_array = []
        schema_objects = self.schema["components"]["schemas"]
        for s in schema_objects.keys():
        # each of these is potentially an MoH schema, e.g. Donor, or Treatment
        # skip the ones that are internal to katsu
            for test in self.skipped_schemas:
                if re.search(test,s):
                    break
            else: 
                schema_array.append(f"# Schema {s}\n")
                properties = schema_objects[s]["properties"]
                for k in properties.keys():
                    # format of each line is : schema.field, # help text 
                    schema_array.append(f"{s}.{k}, ## add mapping function here\n")
        return schema_array

    def generate_scaffold(self):
        """Generate a simplied version of the schema with only the schema 
        objects that are not in skipped_schemas. Similar code as 
        generate_schema_array but returns a dict instead of an array."""
        scaffold = {}
        schema_objects = self.schema["components"]["schemas"]
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
            return self.schema["components"]["schemas"][schema_name]
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



