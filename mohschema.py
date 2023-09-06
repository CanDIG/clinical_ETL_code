import json
import dateparser
from schema import BaseSchema, ValidationError


"""
A class for the representation of a DonorWithClinicalData (MoHCCN data model v2) object in Katsu.
"""

class MoHSchema(BaseSchema):
    schema_name = "DonorWithClinicalData"


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
                "date_of_birth",
                "primary_site"
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
                "basis_of_diagnosis",
                "lymph_nodes_examined_status"
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
                "treatment_setting",
                "treatment_intent",
                "response_to_treatment_criteria_method",
                "response_to_treatment"
            ],
            "nested_schemas": [
                "chemotherapies",
                "hormone_therapies",
                "immunotherapies",
                "radiation",
                "surgery",
                "followups",
                "biomarkers"
            ]
        },
        "chemotherapies": {
            "id": None,
            "name": "Chemotherapy",
            "required_fields": [
                "drug_reference_database",
                "drug_name",
                "drug_reference_identifier"
            ],
            "nested_schemas": []
        },
        "hormone_therapies": {
            "id": None,
            "name": "Hormone Therapy",
            "required_fields": [
                "drug_reference_database",
                "drug_name",
                "drug_reference_identifier"
            ],
            "nested_schemas": []
        },
        "immunotherapies": {
            "id": None,
            "name": "Immunotherapy",
            "required_fields": [
                "drug_reference_database",
                "drug_name",
                "drug_reference_identifier"
            ],
            "nested_schemas": []
        },
        "radiation": {
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
        "surgery": {
            "id": None,
            "name": "Surgery",
            "required_fields": [
                "surgery_type"
            ],
            "nested_schemas": []
        },
        "biomarkers": {
            "id": None,
            "name": "Biomarker",
            "required_fields": [
                "submitter_sample_id",
                "specimen_tissue_source",
                "specimen_type",
                "sample_type"
            ],
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


    def validate_donors(self, map_json):
        for prop in map_json:
            match prop:
                case "is_deceased":
                    if map_json["is_deceased"]:
                        if "cause_of_death" not in map_json:
                            self.warn("cause_of_death required if is_deceased = Yes")
                        if "date_of_death" not in map_json:
                            self.warn("date_of_death required if is_deceased = Yes")
                case "lost_to_followup_after_clinical_event_identifier":
                    if map_json["is_deceased"]:
                        self.warn("lost_to_followup_after_clinical_event_identifier cannot be present if is_deceased = Yes")
                case "lost_to_followup_reason":
                    if "lost_to_followup_after_clinical_event_identifier" not in map_json:
                        self.warn("lost_to_followup_reason should only be submitted if lost_to_followup_after_clinical_event_identifier is submitted")
                case "date_alive_after_lost_to_followup":
                    if "lost_to_followup_after_clinical_event_identifier" not in map_json:
                        self.warn("lost_to_followup_after_clinical_event_identifier needs to be submitted if date_alive_after_lost_to_followup is submitted")
                case "cause_of_death":
                    if not map_json["is_deceased"]:
                        self.warn("cause_of_death should only be submitted if is_deceased = Yes")
                case "date_of_death":
                    if not map_json["is_deceased"]:
                        self.warn("date_of_death should only be submitted if is_deceased = Yes")
                    else:
                        if map_json["date_of_death"] is not None and map_json["date_of_birth"] is not None:
                            death = dateparser.parse(map_json["date_of_death"]).date()
                            birth = dateparser.parse(map_json["date_of_birth"]).date()
                            if birth > death:
                                self.warn("date_of_death cannot be earlier than date_of_birth")
                case "biomarkers":
                    for x in map_json["biomarkers"]:
                        if "test_date" not in x:
                            self.warn("test_date is necessary for biomarkers not associated with nested events")


    def validate_primary_diagnoses(self, map_json):
        # check to see if this primary_diagnosis is a tumour:
        specimen_ids = []
        is_tumour = False
        # should either have a clinical staging system specified
        # OR have a specimen with a pathological staging system specified
        if "clinical_tumour_staging_system" in map_json:
            is_tumour = True
        if "specimens" in map_json:
            for specimen in map_json["specimens"]:
                specimen_ids.append(specimen["submitter_specimen_id"])
                if "pathological_tumour_staging_system" in specimen:
                    is_tumour = True

        self.validation_schema["primary_diagnoses"]["extra_args"]["specimen_ids"] = specimen_ids
        self.validation_schema["primary_diagnoses"]["extra_args"]["is_tumour"] = is_tumour

        for prop in map_json:
            match prop:
                case "lymph_nodes_examined_status":
                    if map_json["lymph_nodes_examined_status"]:
                        if "lymph_nodes_examined_method" not in map_json:
                            self.warn("lymph_nodes_examined_method required if lymph_nodes_examined_status = Yes")
                        if "number_lymph_nodes_positive" not in map_json:
                            self.warn("number_lymph_nodes_positive required if lymph_nodes_examined_status = Yes")
                case "clinical_tumour_staging_system":
                    self.validate_staging_system(map_json, "clinical")


    def validate_specimens(self, map_json):
        is_clinical_tumour = self.validation_schema["primary_diagnoses"]["extra_args"]["is_tumour"]
        # Presence of tumour_histological_type means we have a tumour sample
        if "tumour_histological_type" in map_json:
            if not is_clinical_tumour:
                if "pathological_tumour_staging_system" not in map_json:
                    self.warn("Tumour specimens without clinical_tumour_staging_system require a pathological_tumour_staging_system")
                else:
                    self.validate_staging_system(map_json, "pathological")
            required_fields = [
                "reference_pathology_confirmed_diagnosis",
                "reference_pathology_confirmed_tumour_presence",
                "tumour_grading_system",
                "tumour_grade",
                "percent_tumour_cells_range",
                "percent_tumour_cells_measurement_method"
            ]
            for f in required_fields:
                if f not in map_json:
                    self.warn(f"Tumour specimens require a {f}")


    def validate_sample_registrations(self, map_json):
        # there aren't any additional validations here
        return


    def validate_biomarkers(self, map_json):
        for prop in map_json:
            match prop:
                case "hpv_pcr_status":
                    if map_json["hpv_pcr_status"] == "Positive" and "hpv_strain" not in map_json:
                        self.warn("If hpv_pcr_status is positive, hpv_strain is required")


    def validate_followups(self, map_json):
        for prop in map_json:
            match prop:
                case "disease_status_at_followup":
                    states = [
                        "Distant progression",
                        "Loco-regional progression",
                        "Progression not otherwise specified",
                        "Relapse or recurrence"
                    ]
                    if map_json["disease_status_at_followup"] in states:
                        required_fields = [
                            "relapse_type",
                            "date_of_relapse",
                            "method_of_progression_status"
                        ]
                        for field in required_fields:
                            if field not in map_json:
                                self.warn(f"{field} is required if disease_status_at_followup is {map_json['disease_status_at_followup']}")
                        if "anatomic_site_progression_or_recurrence" not in map_json:
                            if "relapse_type" in map_json and map_json["relapse_type"] != "Biochemical progression":
                                self.warn(f"anatomic_site_progression_or_recurrence is required if disease_status_at_followup is {map_json['disease_status_at_followup']}")


    def validate_treatments(self, map_json):
        for prop in map_json:
            match prop:
                case "treatment_type":
                    for type in map_json["treatment_type"]:
                        match type:
                            case "Chemotherapy":
                                if "chemotherapies" not in map_json:
                                    self.warn("treatment type Chemotherapy should have one or more chemotherapies submitted")
                            case "Hormonal therapy":
                                if "hormone_therapies" not in map_json:
                                    self.warn("treatment type Hormonal therapy should have one or more hormone_therapies submitted")
                            case "Immunotherapy":
                                if "immunotherapies" not in map_json:
                                    self.warn("treatment type Immunotherapy should have one or more immunotherapies submitted")
                            case "Radiation therapy":
                                if "radiations" not in map_json:
                                    self.warn("treatment type Radiation therapy should have one or more radiation submitted")
                            case "Surgery":
                                if "surgeries" not in map_json:
                                    self.warn("treatment type Surgery should have one or more surgery submitted")


    def validate_chemotherapies(self, map_json):
        for prop in map_json:
            match prop:
                case "prescribed_cumulative_drug_dose":
                    if "chemotherapy_drug_dose_units" not in map_json:
                        self.warn("chemotherapy_drug_dose_units required if prescribed_cumulative_drug_dose is submitted")
                case "actual_cumulative_drug_dose":
                    if "chemotherapy_drug_dose_units" not in map_json:
                        self.warn("chemotherapy_drug_dose_units required if actual_cumulative_drug_dose is submitted")


    def validate_hormone_therapies(self, map_json):
        for prop in map_json:
            match prop:
                case "prescribed_cumulative_drug_dose":
                    if "hormone_drug_dose_units" not in map_json:
                        self.warn("hormone_drug_dose_units required if prescribed_cumulative_drug_dose is submitted")
                case "actual_cumulative_drug_dose":
                    if "hormone_drug_dose_units" not in map_json:
                        self.warn("hormone_drug_dose_units required if actual_cumulative_drug_dose is submitted")


    def validate_immunotherapies(self, map_json):
        for prop in map_json:
            match prop:
                case "prescribed_cumulative_drug_dose":
                    if "immunotherapy_drug_dose_units" not in map_json:
                        self.warn("immunotherapy_drug_dose_units required if prescribed_cumulative_drug_dose is submitted")
                case "actual_cumulative_drug_dose":
                    if "immunotherapy_drug_dose_units" not in map_json:
                        self.warn("immunotherapy_drug_dose_units required if actual_cumulative_drug_dose is submitted")


    def validate_radiation(self, map_json):
        index = self.validation_schema["radiation"]["extra_args"]["index"]
        if index > 0:
            self.warn("Only one radiation is allowed per treatment")

        for prop in map_json:
            match prop:
                case "radiation_boost":
                    if map_json["radiation_boost"]:
                        if "reference_radiation_treatment_id" not in map_json:
                            self.warn("reference_radiation_treatment_id required if radiation_boost = Yes")


    def validate_surgery(self, map_json):
        specimen_ids = self.validation_schema["primary_diagnoses"]["extra_args"]["specimen_ids"]
        index = self.validation_schema["surgery"]["extra_args"]["index"]
        if index > 0:
            self.warn("Only one surgery is allowed per treatment")

        if "submitter_specimen_id" not in map_json:
            if "surgery_site" not in map_json:
                self.warn("surgery_site required if submitter_specimen_id not submitted")
            if "surgery_location" not in map_json:
                self.warn("surgery_location required if submitter_specimen_id not submitted")
        else:
            if map_json["submitter_specimen_id"] not in specimen_ids:
                self.warn(f"submitter_specimen_id {map_json['submitter_specimen_id']} does not correspond to one of the available specimen_ids {specimen_ids}")


    def validate_comorbidities(self, map_json):
        for prop in map_json:
            match prop:
                case "laterality_of_prior_malignancy":
                    if "prior_malignancy" not in map_json or map_json["prior_malignancy"] != "Yes":
                        self.warn("laterality_of_prior_malignancy should not be submitted unless prior_malignancy = Yes")


    def validate_exposures(self, map_json):
        is_smoker = False
        if "tobacco_smoking_status" not in map_json:
            self.fail("tobacco_smoking_status required for exposure")
        else:
            if map_json["tobacco_smoking_status"] in [
                "Current reformed smoker for <= 15 years",
                "Current reformed smoker for > 15 years",
                "Current reformed smoker, duration not specified",
                "Current smoker"
            ]:
                is_smoker = True

        for prop in map_json:
            match prop:
                case "tobacco_type":
                    if not is_smoker:
                        self.warn(f"tobacco_type cannot be submitted for tobacco_smoking_status = {map_json['tobacco_smoking_status']}")
                case "pack_years_smoked":
                    if not is_smoker:
                        self.warn(f"pack_years_smoked cannot be submitted for tobacco_smoking_status = {map_json['tobacco_smoking_status']}")


    def validate_staging_system(self, map_json, staging_type):
        if "AJCC" in map_json[f"{staging_type}_tumour_staging_system"]:
            required_fields = [
                "t_category",
                "n_category",
                "m_category"
            ]
            for f in required_fields:
                if f"{staging_type}_{f}" not in map_json:
                    self.warn(f"{staging_type}_{f} is required if {staging_type}_tumour_staging_system is AJCC")
        else:
            if f"{staging_type}_stage_group" not in map_json:
                self.warn(f"{staging_type}_stage_group is required for {staging_type}_tumour_staging_system {map_json[f'{staging_type}_tumour_staging_system']}")
