# mappings and validation based on the mohccn schema

import requests
import yaml
import json
import re
from copy import deepcopy
import jsonschema
import dateparser


VALIDATION_MESSAGES = []


class MoHValidationError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(f"Validation error: {self.value}")


def warn(message):
    VALIDATION_MESSAGES.append(f"{message}")
    # raise MoHValidationError(message)


def fail(message):
    raise MoHValidationError(message)


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

        # create the template for the schema_name schema
        self.scaffold = self.generate_schema_scaffold(self.schema[self.schema_name])
        # print(json.dumps(self.scaffold, indent=4))
        _, raw_template = self.generate_mapping_template(self.scaffold)

        # add default mapping functions:
        self.template = self.add_default_mappings(raw_template)


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
        elif "allOf" in schema_obj:
            result = self.expand_ref(schema_obj["allOf"][0])
        elif "oneOf" in schema_obj:
            result = self.expand_ref(schema_obj["oneOf"][0])
        elif "anyOf" in schema_obj:
            result = self.expand_ref(schema_obj["anyOf"][0])
        else:
            result = "unknown"
        return result


    def generate_mapping_template(self, node, node_name="", node_names=None):
        """Create a template for mohschema, for use with the --template flag."""
        if node_names is None:
            node_names = []
        if node_name != "" and not node_name.endswith(".id"):
            # check to see if the last node_name is a header for this node_name:
            if len(node_names) > 0:
                x = node_names.pop()
                x_match = re.match(r"(.+),", x)
                if x_match is not None:
                    if x.endswith(".INDEX,"):
                        node_names.append(x)
                    elif x_match.group(1) not in node_name:
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


    def add_default_mappings(self, template):
        # if line ends in INDEX, use indexed_on
        # otherwise, single_val
        result = []
        index_stack = []
        for i in range(0, len(template)):
            # work with line w/o comma
            x = template[i]
            if x.startswith("##"):
                continue

            x_match = re.match(r"(.+),", x)
            if x_match is not None:
                field = x_match.group(1)
                field_bits = field.split(".")
                data_value = field_bits[-1]

                # adjust the size of the stack: if it's bigger than the number of INDEX in the line, trim the stack back
                num_indices = field_bits.count("INDEX")
                if len(index_stack) > num_indices:
                    index_stack = index_stack[0:num_indices]

                if field_bits[-1] == "INDEX":
                    # base case: assume that the index_value is the last bit before the index
                    data_value = field_bits[len(field_bits)-2]

                    # next case: data value could be the the next line's last bit:
                    # prev: primary_site.INDEX
                    # CURR: primary_diagnoses.INDEX
                    # NEXT: primary_diagnoses.INDEX.submitter_primary_diagnosis_id
                    next_line = template[i+1]
                    next_match = re.match(r"(.+),", next_line)
                    next_bits = next_match.group(1).split(".")
                    if field in next_line:
                        # if the next line is a nested version of field, we need to think about the stack
                        data_value = next_bits[-1]

                        # but...do we need to un-nest?
                        # this index is NOT a nested entry of the prev one; we need to figure out how far back to un-nest.
                        if len(index_stack) > 0:
                            prev_line = template[i-1]
                            if field not in prev_line:
                                prev_match = re.match(r"(.+),", prev_line)
                                prev_bits = prev_match.group(1).split(".")
                                # if prev_bits does not end on INDEX, needs to be trimmed back before its last INDEX:
                                if prev_bits[-1] != "INDEX":
                                    while len(prev_bits) > 0:
                                        if prev_bits[-1] != "INDEX":
                                            prev_bits.pop()
                                        else:
                                            break
                                # bounce off the last two bits from field_bits and one from the stack
                                done = False
                                count = 0
                                while 1:
                                    if len(field_bits) == 0:
                                        count = 0
                                        break
                                    # if this is now the same, we're done
                                    if (".".join(prev_bits) == ".".join(field_bits)):
                                        break
                                    if ".".join(prev_bits) not in ".".join(field_bits):
                                        count += 1
                                        break
                                    field_bits.pop()
                                    field_bits.pop()
                                for i in range(0, count):
                                    index_stack.pop()

                        # this should be added to the stack, but not if the value is "INDEX"
                        if data_value != "INDEX":
                            index_stack.append(data_value)
                            if len(index_stack) > 1:
                                data_value = index_stack[-2]
                    x += f" {{indexed_on({data_value})}}"
                elif field_bits[-1].endswith("date") or field_bits[-1].startswith("date"):
                    x += f" {{single_date({data_value})}}"
                elif field_bits[-1].startswith("is_") or field_bits[-1].startswith("has_"):
                    x += f" {{boolean({data_value})}}"
                elif field_bits[-1].startswith("number_") or field_bits[-1].startswith("age_") or "_per_" in field_bits[-1]:
                    x += f" {{integer({data_value})}}"
                else:
                    x += f" {{single_val({data_value})}}"
                result.append(x)
        return result


    def validate_donor(self, donor_json):
        global VALIDATION_MESSAGES
        VALIDATION_MESSAGES = []
        if "submitter_donor_id" in donor_json:
            print(f"Validating schema for donor {donor_json['submitter_donor_id']}...")
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
                fail(f"{f} required for Donor")

        for prop in donor_json:
            match prop:
                case "is_deceased":
                    if donor_json["is_deceased"]:
                        if "cause_of_death" not in donor_json:
                            warn("cause_of_death required if is_deceased = Yes")
                        if "date_of_death" not in donor_json:
                            warn("date_of_death required if is_deceased = Yes")
                case "lost_to_followup_after_clinical_event_identifier":
                    if donor_json["is_deceased"]:
                        warn("lost_to_followup_after_clinical_event_identifier cannot be present if is_deceased = Yes")
                case "lost_to_followup_reason":
                    if "lost_to_followup_after_clinical_event_identifier" not in donor_json:
                        warn("lost_to_followup_reason should only be submitted if lost_to_followup_after_clinical_event_identifier is submitted")
                case "date_alive_after_lost_to_followup":
                    if "lost_to_followup_after_clinical_event_identifier" not in donor_json:
                        warn("lost_to_followup_after_clinical_event_identifier needs to be submitted if date_alive_after_lost_to_followup is submitted")
                case "cause_of_death":
                    if not donor_json["is_deceased"]:
                        warn("cause_of_death should only be submitted if is_deceased = Yes")
                case "date_of_death":
                    if not donor_json["is_deceased"]:
                        warn("date_of_death should only be submitted if is_deceased = Yes")
                    else:
                        death = dateparser.parse(donor_json["date_of_death"]).date()
                        birth = dateparser.parse(donor_json["date_of_birth"]).date()
                        if birth > death:
                            warn("date_of_death cannot be earlier than date_of_birth")
                case "primary_diagnoses":
                    for x in donor_json["primary_diagnoses"]:
                        self.validate_primary_diagnosis(x)
                case "comorbidities":
                    for x in donor_json["comorbidities"]:
                        self.validate_comorbidity(x)
                case "exposures":
                    for x in donor_json["exposures"]:
                        self.validate_exposure(x)
                case "biomarkers":
                    for x in donor_json["biomarkers"]:
                        if "test_date" not in x:
                            warn("test_date is necessary for biomarkers not associated with nested events")
                        else:
                            self.validate_biomarker(x, "test_date", x["test_date"])
                case "followups":
                    for x in donor_json["followups"]:
                        self.validate_followup(x)
        return VALIDATION_MESSAGES

    def validate_primary_diagnosis(self, map_json):
        print(f"Validating schema for primary_diagnosis {map_json['submitter_primary_diagnosis_id']}...")
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
                fail(f"{f} required for primary_diagnosis")

        is_tumour = False
        # should either have a clinical staging system specified
        # OR have a specimen with a pathological staging system specified
        if "clinical_tumour_staging_system" in map_json:
            is_tumour = True
        elif "specimens" in map_json:
            for specimen in map_json["specimens"]:
                if "pathological_tumour_staging_system" in specimen:
                    is_tumour = True

        for prop in map_json:
            match prop:
                case "lymph_nodes_examined_status":
                    if map_json["lymph_nodes_examined_status"]:
                        if "lymph_nodes_examined_method" not in map_json:
                            warn("lymph_nodes_examined_method required if lymph_nodes_examined_status = Yes")
                        if "number_lymph_nodes_positive" not in map_json:
                            warn("number_lymph_nodes_positive required if lymph_nodes_examined_status = Yes")
                case "clinical_tumour_staging_system":
                    self.validate_staging_system(map_json, "clinical")
                case "specimens":
                    for specimen in map_json["specimens"]:
                        self.validate_specimen(specimen, "clinical_tumour_staging_system" in map_json)
                case "treatments":
                    for treatment in map_json["treatments"]:
                        self.validate_treatment(treatment)
                case "biomarkers":
                    for biomarker in map_json["biomarkers"]:
                        self.validate_biomarker(biomarker, "submitter_primary_diagnosis_id", map_json["submitter_primary_diagnosis_id"])
                case "followups":
                    for followup in map_json["followups"]:
                        self.validate_followup(followup)


    def validate_specimen(self, map_json, is_clinical_tumour):
        print(f"Validating schema for specimen {map_json['submitter_specimen_id']}...")

        required_fields = [
            "submitter_specimen_id",
            "specimen_collection_date",
            "specimen_storage",
            "specimen_anatomic_location"
        ]
        for f in required_fields:
            if f not in map_json:
                fail(f"{f} required for specimen")

        # Presence of tumour_histological_type means we have a tumour sample
        if "tumour_histological_type" in map_json:
            if not is_clinical_tumour:
                if "pathological_tumour_staging_system" not in map_json:
                    warn("Tumour specimens without clinical_tumour_staging_system require a pathological_tumour_staging_system")
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
                    warn(f"Tumour specimens require a {f}")

        for prop in map_json:
            match prop:
                case "sample_registrations":
                    for sample in map_json["sample_registrations"]:
                        self.validate_sample_registration(sample)
                case "biomarkers":
                    for biomarker in map_json["biomarkers"]:
                        self.validate_biomarker(biomarker, "submitter_specimen_id", map_json["submitter_specimen_id"])


    def validate_sample_registration(self, map_json):
        print(f"Validating schema for sample_registration {map_json['submitter_sample_id']}...")

        required_fields = [
            "submitter_sample_id",
            "specimen_tissue_source",
            "specimen_type",
            "sample_type"
        ]
        for f in required_fields:
            if f not in map_json:
                fail(f"{f} required for sample_registration")


    def validate_biomarker(self, map_json, associated_field, associated_value):
        print(f"Validating schema for biomarker associated with {associated_field} {associated_value}...")

        for prop in map_json:
            match prop:
                case "hpv_pcr_status":
                    if map_json["hpv_pcr_status"] == "Positive" and "hpv_strain" not in map_json:
                        warn("If hpv_pcr_status is positive, hpv_strain is required")


    def validate_followup(self, map_json):
        print(f"Validating schema for followup {map_json['submitter_follow_up_id']}...")

        required_fields = [
            "date_of_followup",
            "disease_status_at_followup"
        ]
        for f in required_fields:
            if f not in map_json:
                fail(f"{f} required for followup")

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
                                warn(f"{field} is required if disease_status_at_followup is {map_json['disease_status_at_followup']}")
                        if "anatomic_site_progression_or_recurrence" not in map_json:
                            if "relapse_type" in map_json and map_json["relapse_type"] != "Biochemical progression":
                                warn(f"anatomic_site_progression_or_recurrence is required if disease_status_at_followup is {map_json['disease_status_at_followup']}")


    def validate_treatment(self, map_json):
        print(f"Validating schema for treatment {map_json['submitter_treatment_id']}...")

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
                fail(f"{f} required for treatment")

        for prop in map_json:
            match prop:
                case "treatment_type":
                    match map_json["treatment_type"]:
                        case "Chemotherapy":
                            if "chemotherapies" not in map_json:
                                warn("treatment type Chemotherapy should have one or more chemotherapies submitted")
                            else:
                                for x in map_json["chemotherapies"]:
                                    self.validate_chemotherapy(x)
                        case "Hormonal therapy":
                            if "hormone_therapies" not in map_json:
                                warn("treatment type Hormonal therapy should have one or more hormone_therapies submitted")
                            else:
                                for x in map_json["hormone_therapies"]:
                                    self.validate_hormone_therapy(x)
                        case "Immunotherapy":
                            if "immunotherapies" not in map_json:
                                warn("treatment type Immunotherapy should have one or more immunotherapies submitted")
                            else:
                                for x in map_json["immunotherapies"]:
                                    self.validate_immunotherapy(x)
                        case "Radiation therapy":
                            if "radiation" not in map_json:
                                warn("treatment type Radiation therapy should have one or more radiation submitted")
                            else:
                                for x in map_json["radiation"]:
                                    self.validate_radiation(x)
                        case "Surgery":
                            if "surgery" not in map_json:
                                warn("treatment type Surgery should have one or more surgery submitted")
                            else:
                                for x in map_json["surgery"]:
                                    self.validate_surgery(x)
                case "followups":
                    for followup in map_json["followups"]:
                        self.validate_followup(followup)
                case "biomarkers":
                    for biomarker in map_json["biomarkers"]:
                        self.validate_biomarker(biomarker, "submitter_treatment_id", map_json["submitter_treatment_id"])


    def validate_chemotherapy(self, map_json):
        print(f"Validating schema for chemotherapy...")

        required_fields = [
            "drug_reference_database",
            "drug_name",
            "drug_reference_identifier"
        ]
        for f in required_fields:
            if f not in map_json:
                fail(f"{f} required for chemotherapy")

        for prop in map_json:
            match prop:
                case "prescribed_cumulative_drug_dose":
                    if "chemotherapy_drug_dose_units" not in map_json:
                        warn("chemotherapy_drug_dose_units required if prescribed_cumulative_drug_dose is submitted")
                case "actual_cumulative_drug_dose":
                    if "chemotherapy_drug_dose_units" not in map_json:
                        warn("chemotherapy_drug_dose_units required if actual_cumulative_drug_dose is submitted")


    def validate_hormone_therapy(self, map_json):
        print(f"Validating schema for hormone_therapy...")

        required_fields = [
            "drug_reference_database",
            "drug_name",
            "drug_reference_identifier"
        ]
        for f in required_fields:
            if f not in map_json:
                fail(f"{f} required for hormone_therapy")

        for prop in map_json:
            match prop:
                case "prescribed_cumulative_drug_dose":
                    if "hormone_drug_dose_units" not in map_json:
                        warn("hormone_drug_dose_units required if prescribed_cumulative_drug_dose is submitted")
                case "actual_cumulative_drug_dose":
                    if "hormone_drug_dose_units" not in map_json:
                        warn("hormone_drug_dose_units required if actual_cumulative_drug_dose is submitted")


    def validate_immunotherapy(self, map_json):
        print(f"Validating schema for immunotherapy...")

        required_fields = [
            "drug_reference_database",
            "drug_name",
            "drug_reference_identifier"
        ]
        for f in required_fields:
            if f not in map_json:
                fail(f"{f} required for immunotherapy")

        for prop in map_json:
            match prop:
                case "prescribed_cumulative_drug_dose":
                    if "immunotherapy_drug_dose_units" not in map_json:
                        warn("immunotherapy_drug_dose_units required if prescribed_cumulative_drug_dose is submitted")
                case "actual_cumulative_drug_dose":
                    if "immunotherapy_drug_dose_units" not in map_json:
                        warn("immunotherapy_drug_dose_units required if actual_cumulative_drug_dose is submitted")


    def validate_radiation(self, map_json):
        print(f"Validating schema for radiation...")

        required_fields = [
            "radiation_therapy_modality",
            "radiation_therapy_type",
            "anatomical_site_irradiated",
            "radiation_therapy_fractions",
            "radiation_therapy_dosage"
        ]
        for f in required_fields:
            if f not in map_json:
                fail(f"{f} required for radiation")

        for prop in map_json:
            match prop:
                case "radiation_boost":
                    if map_json["radiation_boost"]:
                        if "reference_radiation_treatment_id" not in map_json:
                            warn("reference_radiation_treatment_id required if radiation_boost = Yes")


    def validate_surgery(self, map_json):
        print(f"Validating schema for surgery...")

        required_fields = [
            "surgery_type"
        ]
        for f in required_fields:
            if f not in map_json:
                fail(f"{f} required for surgery")

        if "submitter_specimen_id" not in map_json:
            if "surgery_site" not in map_json:
                warn("surgery_site required if submitter_specimen_id not submitted")
            if "surgery_location" not in map_json:
                warn("surgery_location required if submitter_specimen_id not submitted")


    def validate_comorbidity(self, map_json):
        print(f"Validating schema for comorbidity...")

        required_fields = [
            "comorbidity_type_code"
        ]
        for f in required_fields:
            if f not in map_json:
                fail(f"{f} required for comorbidity")

        for prop in map_json:
            match prop:
                case "laterality_of_prior_malignancy":
                    if "prior_malignancy" not in map_json or map_json["prior_malignancy"] != "Yes":
                        warn("laterality_of_prior_malignancy should not be submitted unless prior_malignancy = Yes")


    def validate_exposure(self, map_json):
        print(f"Validating schema for exposure...")

        is_smoker = False
        if "tobacco_smoking_status" not in map_json:
            fail("tobacco_smoking_status required for exposure")
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
                        warn(f"tobacco_type cannot be submitted for tobacco_smoking_status = {map_json['tobacco_smoking_status']}")
                case "pack_years_smoked":
                    if not is_smoker:
                        warn(f"pack_years_smoked cannot be submitted for tobacco_smoking_status = {map_json['tobacco_smoking_status']}")


    def validate_staging_system(self, map_json, staging_type):
        if "AJCC" in map_json[f"{staging_type}_tumour_staging_system"]:
            required_fields = [
                "t_category",
                "n_category",
                "m_category"
            ]
            for f in required_fields:
                if f"{staging_type}_{f}" not in map_json:
                    warn(f"{staging_type}_{f} is required if {staging_type}_tumour_staging_system is AJCC")
        else:
            if "{staging_type}_stage_group" not in map_json:
                warn(f"{staging_type}_stage_group is required for {staging_type}_tumour_staging_system {map_json[f'{staging_type}_tumour_staging_system']}")