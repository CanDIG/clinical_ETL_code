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

    def __init__(self,url):
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
        components = self.schema["components"]["schemas"]
        schema_array = []
        for component in components.keys():
        # each of these is potentially an MoH schema, e.g. Donor, or Treatment
        # skip the ones that are internal to katsu
            if re.match("Patched",component):
                continue 
            if re.match("Paginated",component):
                continue 
            if re.match("Discovery",component):
                continue 
            if re.search("Request",component):
                continue 
            if re.match("data_ingest",component):
                continue 
            if re.match("moh",component):
                continue 
            if re.search("Enum", component):
                continue
            schema_array.append(f"# Schema {component}\n")
            properties = components[component]["properties"]
            for k in properties.keys():
                # format of each line is : schema.field, # help text 
                schema_array.append(f"{component}.{k}, ## add mapping function here\n")
        return schema_array

    def get_schema_data(self, schema_name):
        """Given the name of a schema object, return the type"""
        try:
            return self.schema["components"]["schemas"][schema_name]
        except KeyError:
            raise KeyError(f"No schema oject {schema_name} in schema")
            

    def get_schema_type(self, schema_name):
        """Given the name of a schema object, return the type"""
        schema_data = self.get_schema_data(schema_name)
        return schema_data['type']

    def get_property_type(self,schema_name,node):
        """Given the name of a schema object, and a property of that node, 
        return the type"""
        schema_data = self.get_schema_data(schema_name)
        try:
            node_data = schema_data['properties'][node]
            return node_data['type']
        except KeyError:
            raise KeyError(f"No property {node} for {schema_name}")        



