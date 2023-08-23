# mappings and validation based on the mohccn schema

import requests
import yaml
import json
import re
from copy import deepcopy
import jsonschema
import dateparser
from schema import BaseSchema, ValidationError


"""
A class for the representation of a DonorWithClinicalData object in Katsu.
"""

class MoHSchema(BaseSchema):
    schema_name = "DonorWithClinicalData"


    def validate_donor(self, donor_json):
        self.validation_messages = []
        if "submitter_donor_id" in donor_json:
            self.stack_location.append(donor_json['submitter_donor_id'])
            print(f"Validating schema for donor {self.stack_location[-1]}...")
        # validate with jsonschema:
        jsonschema.validate(donor_json, self.json_schema)

        # validate against extra rules in MoH Clinical Data Model v2
        required_fields = [
            "submitter_donor_id",
            "gender",
            "sex_at_birth",
            "is_deceased",
            "program_id",
            "date_of_birth",
            "primary_site"
        ]
        for f in required_fields:
            if f not in donor_json:
                self.fail(f"{f} required for Donor")

        for prop in donor_json:
            match prop:
                case "is_deceased":
                    if donor_json["is_deceased"]:
                        if "cause_of_death" not in donor_json:
                            self.warn("cause_of_death required if is_deceased = Yes")
                        if "date_of_death" not in donor_json:
                            self.warn("date_of_death required if is_deceased = Yes")
                case "lost_to_followup_after_clinical_event_identifier":
                    if donor_json["is_deceased"]:
                        self.warn("lost_to_followup_after_clinical_event_identifier cannot be present if is_deceased = Yes")
                case "lost_to_followup_reason":
                    if "lost_to_followup_after_clinical_event_identifier" not in donor_json:
                        self.warn("lost_to_followup_reason should only be submitted if lost_to_followup_after_clinical_event_identifier is submitted")
                case "date_alive_after_lost_to_followup":
                    if "lost_to_followup_after_clinical_event_identifier" not in donor_json:
                        self.warn("lost_to_followup_after_clinical_event_identifier needs to be submitted if date_alive_after_lost_to_followup is submitted")
                case "cause_of_death":
                    if not donor_json["is_deceased"]:
                        self.warn("cause_of_death should only be submitted if is_deceased = Yes")
                case "date_of_death":
                    if not donor_json["is_deceased"]:
                        self.warn("date_of_death should only be submitted if is_deceased = Yes")
                    else:
                        if donor_json["date_of_death"] is not None and donor_json["date_of_birth"] is not None:
                            death = dateparser.parse(donor_json["date_of_death"]).date()
                            birth = dateparser.parse(donor_json["date_of_birth"]).date()
                            if birth > death:
                                self.warn("date_of_death cannot be earlier than date_of_birth")
                case "primary_diagnoses":
                    for x in donor_json["primary_diagnoses"]:
                        self.validate_primary_diagnosis(x)
                case "comorbidities":
                    for x in range(0, len(donor_json["comorbidities"])):
                        self.validate_comorbidity(donor_json["comorbidities"][x], x)
                case "exposures":
                    for x in range(0, len(donor_json["exposures"])):
                        self.validate_exposure(donor_json["exposures"][x], x)
                case "biomarkers":
                    for x in donor_json["biomarkers"]:
                        if "test_date" not in x:
                            self.warn("test_date is necessary for biomarkers not associated with nested events")
                        else:
                            self.validate_biomarker(x, "test_date", x["test_date"])
                case "followups":
                    for x in donor_json["followups"]:
                        self.validate_followup(x)
        if len(self.stack_location) > 0:
            self.stack_location.pop()
        return self.validation_messages

    def validate_primary_diagnosis(self, map_json):
        self.stack_location.append(map_json['submitter_primary_diagnosis_id'])
        print(f"Validating schema for primary_diagnosis {self.stack_location[-1]}...")
        # check to see if this primary_diagnosis is a tumour:
        required_fields = [
            "submitter_primary_diagnosis_id",
            "date_of_diagnosis",
            "cancer_type_code",
            "basis_of_diagnosis",
            "lymph_nodes_examined_status"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for primary_diagnosis")

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
                case "specimens":
                    for specimen in map_json["specimens"]:
                        self.validate_specimen(specimen, "clinical_tumour_staging_system" in map_json)
                case "treatments":
                    for treatment in map_json["treatments"]:
                        self.validate_treatment(treatment, specimen_ids)
                case "biomarkers":
                    for biomarker in map_json["biomarkers"]:
                        self.validate_biomarker(biomarker, "submitter_primary_diagnosis_id", map_json["submitter_primary_diagnosis_id"])
                case "followups":
                    for followup in map_json["followups"]:
                        self.validate_followup(followup)
        self.stack_location.pop()


    def validate_specimen(self, map_json, is_clinical_tumour):
        self.stack_location.append(map_json['submitter_specimen_id'])
        print(f"Validating schema for specimen {self.stack_location[-1]}...")

        required_fields = [
            "submitter_specimen_id",
            "specimen_collection_date",
            "specimen_storage",
            "specimen_anatomic_location"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for specimen")

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

        for prop in map_json:
            match prop:
                case "sample_registrations":
                    for sample in map_json["sample_registrations"]:
                        self.validate_sample_registration(sample)
                case "biomarkers":
                    for biomarker in map_json["biomarkers"]:
                        self.validate_biomarker(biomarker, "submitter_specimen_id", map_json["submitter_specimen_id"])
        self.stack_location.pop()


    def validate_sample_registration(self, map_json):
        self.stack_location.append(map_json['submitter_sample_id'])
        print(f"Validating schema for sample_registration {self.stack_location[-1]}...")

        required_fields = [
            "submitter_sample_id",
            "specimen_tissue_source",
            "specimen_type",
            "sample_type"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for sample_registration")
        self.stack_location.pop()


    def validate_biomarker(self, map_json, associated_field, associated_value):
        self.stack_location.append(f"{associated_field} {associated_value}")
        print(f"Validating schema for biomarker associated with {self.stack_location[-1]}...")

        for prop in map_json:
            match prop:
                case "hpv_pcr_status":
                    if map_json["hpv_pcr_status"] == "Positive" and "hpv_strain" not in map_json:
                        self.warn("If hpv_pcr_status is positive, hpv_strain is required")
        self.stack_location.pop()


    def validate_followup(self, map_json):
        self.stack_location.append(map_json['submitter_follow_up_id'])
        print(f"Validating schema for followup {self.stack_location[-1]}...")

        required_fields = [
            "submitter_follow_up_id",
            "date_of_followup",
            "disease_status_at_followup"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for followup")

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
        self.stack_location.pop()


    def validate_treatment(self, map_json, specimen_ids):
        self.stack_location.append(map_json['submitter_treatment_id'])
        print(f"Validating schema for treatment {self.stack_location[-1]}...")

        required_fields = [
            "submitter_treatment_id",
            "treatment_type",
            "is_primary_treatment",
            "treatment_start_date",
            "treatment_end_date",
            "treatment_setting",
            "treatment_intent",
            "response_to_treatment_criteria_method",
            "response_to_treatment"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for treatment")

        for prop in map_json:
            match prop:
                case "treatment_type":
                    for type in map_json["treatment_type"]:
                        match type:
                            case "Chemotherapy":
                                if "chemotherapies" not in map_json:
                                    self.warn("treatment type Chemotherapy should have one or more chemotherapies submitted")
                                else:
                                    for x in range(0, len(map_json["chemotherapies"])):
                                        self.validate_chemotherapy(map_json["chemotherapies"][x], x)
                            case "Hormonal therapy":
                                if "hormone_therapies" not in map_json:
                                    self.warn("treatment type Hormonal therapy should have one or more hormone_therapies submitted")
                                else:
                                    for x in range(0, len(map_json["hormone_therapies"])):
                                        self.validate_hormone_therapy(map_json["hormone_therapies"][x], x)
                            case "Immunotherapy":
                                if "immunotherapies" not in map_json:
                                    self.warn("treatment type Immunotherapy should have one or more immunotherapies submitted")
                                else:
                                    for x in range(0, len(map_json["immunotherapies"])):
                                        self.validate_immunotherapy(map_json["immunotherapies"][x], x)
                            case "Radiation therapy":
                                if "radiation" not in map_json:
                                    self.warn("treatment type Radiation therapy should have one or more radiation submitted")
                                else:
                                    for x in range(0, len(map_json["radiation"])):
                                        self.validate_radiation(map_json["radiation"][x], x)
                            case "Surgery":
                                if "surgery" not in map_json:
                                    self.warn("treatment type Surgery should have one or more surgery submitted")
                                else:
                                    for x in range(0, len(map_json["surgery"])):
                                        self.validate_surgery(map_json["surgery"][x], specimen_ids, x)
                case "followups":
                    for followup in map_json["followups"]:
                        self.validate_followup(followup)
                case "biomarkers":
                    for biomarker in map_json["biomarkers"]:
                        self.validate_biomarker(biomarker, "submitter_treatment_id", map_json["submitter_treatment_id"])
        self.stack_location.pop()


    def validate_chemotherapy(self, map_json, i):
        self.stack_location.append(f"Chemotherapy")
        print(f"Validating schema for {self.stack_location[-2]} {self.stack_location[-1]} {i}...")

        required_fields = [
            "drug_reference_database",
            "drug_name",
            "drug_reference_identifier"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for chemotherapy")

        for prop in map_json:
            match prop:
                case "prescribed_cumulative_drug_dose":
                    if "chemotherapy_drug_dose_units" not in map_json:
                        self.warn("chemotherapy_drug_dose_units required if prescribed_cumulative_drug_dose is submitted")
                case "actual_cumulative_drug_dose":
                    if "chemotherapy_drug_dose_units" not in map_json:
                        self.warn("chemotherapy_drug_dose_units required if actual_cumulative_drug_dose is submitted")
        self.stack_location.pop()


    def validate_hormone_therapy(self, map_json, i):
        self.stack_location.append(f"Hormone Therapy")
        print(f"Validating schema for {self.stack_location[-2]} {self.stack_location[-1]} {i}...")

        required_fields = [
            "drug_reference_database",
            "drug_name",
            "drug_reference_identifier"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for hormone_therapy")

        for prop in map_json:
            match prop:
                case "prescribed_cumulative_drug_dose":
                    if "hormone_drug_dose_units" not in map_json:
                        self.warn("hormone_drug_dose_units required if prescribed_cumulative_drug_dose is submitted")
                case "actual_cumulative_drug_dose":
                    if "hormone_drug_dose_units" not in map_json:
                        self.warn("hormone_drug_dose_units required if actual_cumulative_drug_dose is submitted")
        self.stack_location.pop()


    def validate_immunotherapy(self, map_json, i):
        self.stack_location.append(f"Immunotherapy")
        print(f"Validating schema for {self.stack_location[-2]} {self.stack_location[-1]} {i}...")

        required_fields = [
            "drug_reference_database",
            "drug_name",
            "drug_reference_identifier"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for immunotherapy")

        for prop in map_json:
            match prop:
                case "prescribed_cumulative_drug_dose":
                    if "immunotherapy_drug_dose_units" not in map_json:
                        self.warn("immunotherapy_drug_dose_units required if prescribed_cumulative_drug_dose is submitted")
                case "actual_cumulative_drug_dose":
                    if "immunotherapy_drug_dose_units" not in map_json:
                        self.warn("immunotherapy_drug_dose_units required if actual_cumulative_drug_dose is submitted")
        self.stack_location.pop()


    def validate_radiation(self, map_json, i):
        self.stack_location.append(f"Radiation")
        print(f"Validating schema for {self.stack_location[-2]} {self.stack_location[-1]} {i}...")

        required_fields = [
            "radiation_therapy_modality",
            "radiation_therapy_type",
            "anatomical_site_irradiated",
            "radiation_therapy_fractions",
            "radiation_therapy_dosage"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for radiation")

        for prop in map_json:
            match prop:
                case "radiation_boost":
                    if map_json["radiation_boost"]:
                        if "reference_radiation_treatment_id" not in map_json:
                            self.warn("reference_radiation_treatment_id required if radiation_boost = Yes")
        self.stack_location.pop()


    def validate_surgery(self, map_json, specimen_ids, i):
        self.stack_location.append(f"Surgery")
        print(f"Validating schema for {self.stack_location[-2]} {self.stack_location[-1]} {i}...")

        required_fields = [
            "surgery_type"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for surgery")

        if "submitter_specimen_id" not in map_json:
            if "surgery_site" not in map_json:
                self.warn("surgery_site required if submitter_specimen_id not submitted")
            if "surgery_location" not in map_json:
                self.warn("surgery_location required if submitter_specimen_id not submitted")
        else:
            if map_json["submitter_specimen_id"] not in specimen_ids:
                self.warn(f"submitter_specimen_id {map_json['submitter_specimen_id']} does not correspond to one of the available specimen_ids {specimen_ids}")

        self.stack_location.pop()


    def validate_comorbidity(self, map_json, i):
        self.stack_location.append(f"Comorbidity")
        print(f"Validating schema for {self.stack_location[-2]} {self.stack_location[-1]} {i}...")

        required_fields = [
            "comorbidity_type_code"
        ]
        for f in required_fields:
            if f not in map_json:
                self.fail(f"{f} required for comorbidity")

        for prop in map_json:
            match prop:
                case "laterality_of_prior_malignancy":
                    if "prior_malignancy" not in map_json or map_json["prior_malignancy"] != "Yes":
                        self.warn("laterality_of_prior_malignancy should not be submitted unless prior_malignancy = Yes")
        self.stack_location.pop()


    def validate_exposure(self, map_json, i):
        self.stack_location.append(f"Exposure")
        print(f"Validating schema for {self.stack_location[-2]} {self.stack_location[-1]} {i}...")

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
        self.self.stack_location.pop()


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
