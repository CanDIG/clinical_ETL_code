import json
import dateparser
from clinical_etl.schema import BaseSchema, ValidationError


"""
A class for the representation of a DonorWithClinicalData (MoHCCN data model v2) object in Katsu.
"""

class MoHSchemaV3(BaseSchema):
    schema_name = "DonorWithClinicalDataSchema"
    base_name = "DONOR"

    ## Following are specific checks for required fields in the MoH data model, as well as checks for conditionals specified in the model.
    validation_schema = {
        "donors": {
            "id": "submitter_donor_id",
            "name": "Donor",
            "required_fields": [
                "submitter_donor_id",
                "gender",
                "sex_at_birth",
                "is_deceased",
                "program_id",
                "date_resolution",
                "date_of_birth",
            ],
            "nested_schemas": [
                "primary_diagnoses",
                "comorbidities",
                "exposures",
                "biomarkers",
                "followups"
            ]
        },
        "primary_diagnoses": {
            "id": "submitter_primary_diagnosis_id",
            "name": "Primary Diagnosis",
            "required_fields": [
                "submitter_primary_diagnosis_id",
                "date_of_diagnosis",
                "cancer_type_code",
                "primary_site",
                "basis_of_diagnosis",
            ],
            "nested_schemas": [
                "specimens",
                "treatments",
                "biomarkers",
                "followups"
            ]
        },
        "specimens": {
            "id": "submitter_specimen_id",
            "name": "Specimen",
            "required_fields": [
                "submitter_specimen_id",
                "specimen_collection_date",
                "specimen_storage",
                "specimen_anatomic_location"
            ],
            "nested_schemas": [
                "sample_registrations",
                "biomarkers"
            ]
        },
        "sample_registrations": {
            "id": "submitter_sample_id",
            "name": "Sample Registration",
            "required_fields": [
                "submitter_sample_id",
                "specimen_tissue_source",
                "specimen_type",
                "sample_type"
            ],
            "nested_schemas": []
        },
        "treatments": {
            "id": "submitter_treatment_id",
            "name": "Treatment",
            "required_fields": [
                "submitter_treatment_id",
                "treatment_type",
                "is_primary_treatment",
                "treatment_start_date",
                "treatment_end_date",
                "treatment_intent",
            ],
            "nested_schemas": [
                "chemotherapies",
                "hormone_therapies",
                "immunotherapies",
                "radiations",
                "surgeries",
                "followups",
                "biomarkers"
            ]
        },
        "systemic_therapies": {
            "id": None,
            "name": "Systemic Therapy",
            "required_fields": [
                "systemic_therapy_type",
                "start_date",
                "end_date",
                "drug_reference_database",
                "drug_reference_identifier",
                "drug_name",
            ],
            "nested_schemas": [],
        },
        "radiations": {
            "id": None,
            "name": "Radiation",
            "required_fields": [
                "radiation_therapy_modality",
                "radiation_therapy_type",
                "anatomical_site_irradiated",
                "radiation_therapy_fractions",
                "radiation_therapy_dosage"
            ],
            "nested_schemas": []
        },
        "surgeries": {
            "id": None,
            "name": "Surgery",
            "required_fields": [
                "surgery_reference_database",
                "surgery_refence_identifier",
                "surgery_type"
            ],
            "nested_schemas": []
        },
        "biomarkers": {
            "id": None,
            "name": "Biomarker",
            "required_fields": [],
            "nested_schemas": []
        },
        "followups": {
            "id": "submitter_follow_up_id",
            "name": "Follow Up",
            "required_fields": [
                "submitter_follow_up_id",
                "date_of_followup",
                "disease_status_at_followup"
            ],
            "nested_schemas": [
                "biomarkers"
            ]
        },
        "comorbidities": {
            "id": None,
            "name": "Comorbidity",
            "required_fields": [
                "comorbidity_type_code"
            ],
            "nested_schemas": []
        },
        "exposures": {
            "id": None,
            "name": "Exposure",
            "required_fields": [],
            "nested_schemas": []
        }
    }
