import json
from schema import BaseSchema, ValidationError


"""
A class for the representation of a SequencingIngest object for candigv2-ingest.
"""


class SequencingIngestSchema(BaseSchema):
    schema_name = "SequencingIngest"
    base_name = "EXPERIMENT"

    ## Following are specific checks for required fields in the MoH data model, as well as checks for conditionals specified in the model.
    validation_schema = \
        {
            "experiments": {
                "id": "experiment_id",
                "name": "Experiment ID",
                "required_fields": [
                    "program_id",
                    "experiment_id",
                    "submitter_sample_id",
                    "metadata"
                ],
                "nested_schemas": []
            },
            "analyses": {
                "id": "analysis_id",
                "name": "Analysis ID",
                "required_field": [
                    "program_id",
                    "analysis_id",
                    "metadata",
                    "main",
                    "samples"
                ],
                "nested_schemas": [
                    "samples"
                ]
            },
            "samples": {
                "id": "submitter_sample_id",
                "name": "Submitter Sample Pairing",
                "required_fields": [
                    "experiment_id",
                    "analysis_sample_id"
                ],
                "nested_schemas": []
            }
        }

    def validate_genomic_ids(self, map_json):
        return

    def validate_samples(self, map_json):
        return
