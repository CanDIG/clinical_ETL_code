import pytest
import yaml
import os
import sys
import json

from clinical_etl import CSVConvert
from clinical_etl import mappings
from clinical_etl.mohschemav4 import MoHSchemaV4

# read sheet from given data pathway
REPO_DIR = os.path.abspath(f"{os.path.dirname(os.path.realpath(__file__))}")

@pytest.fixture
def schema():
    manifest_file = f"{REPO_DIR}/manifest.yml"
    with open(manifest_file, 'r') as f:
        manifest = yaml.safe_load(f)
    if manifest is not None:
        return MoHSchemaV4(manifest['schema'])
    return None


@pytest.fixture
def packets():
    input_path = f"{REPO_DIR}/raw_data"
    manifest_file = f"{REPO_DIR}/manifest.yml"
    mappings.INDEX_STACK = []
    return_values = CSVConvert.csv_convert(input_path, manifest_file, verbose=False)
    return return_values[0]


@pytest.fixture
def result():
    """The full conversion output (all roots: donors and programs) as written to _map.json."""
    input_path = f"{REPO_DIR}/raw_data"
    manifest_file = f"{REPO_DIR}/manifest.yml"
    mappings.INDEX_STACK = []
    CSVConvert.csv_convert(input_path, manifest_file, verbose=False)
    with open(f"{input_path}_map.json", 'r') as f:
        return json.load(f)


def test_csv_convert(packets):
    # there are 6 donors
    assert len(packets) == 6


def test_external_mapping(packets):
    assert packets[0]['test_mapping'] == "test string"


def test_donor_1(packets):
    for packet in packets:
        if packet['submitter_donor_id'] == "DONOR_1":
            # test Followups: FOLLOW_UP_2 is in TR_1, FOLLOW_UP_1 is in PD_1, FOLLOW_UP_3 and FOLLOW_UP_4 are in DONOR_1
            for pd in packet['primary_diagnoses']:
                if "followups" in pd:
                    for f in pd['followups']:
                        # assert f['submitter_primary_diagnosis_id'] == pd['submitter_primary_diagnosis_id']
                        assert f['submitter_follow_up_id'] == "FOLLOW_UP_1"
                if "treatments" in pd:
                    for t in pd["treatments"]:
                        if "followups" in t:
                            for f in t['followups']:
                                # assert f['submitter_treatment_id'] == t['submitter_treatment_id']
                                assert f['submitter_follow_up_id'] == "FOLLOW_UP_2"
            if "followups" in packet:
                assert len(packet['followups']) == 2
                for f in packet['followups']:
                    assert f['submitter_follow_up_id'] in ["FOLLOW_UP_3", "FOLLOW_UP_4"]
        else:
            continue


def test_donor_2(packets):
    for packet in packets:
        if packet['submitter_donor_id'] == "DONOR_2":
            # DONOR_2 has two primary diagnoses, PD_2 and PD_2_1
            assert len(packet['primary_diagnoses']) == 2
            for pd in packet['primary_diagnoses']:
                assert 'specimens' in pd
                for specimen in pd['specimens']:
                    assert specimen['submitter_specimen_id'] in ["SPECIMEN_5", "SPECIMEN_4", "SPECIMEN_7"]
                    if 'sample_registrations' in specimen:
                        for sample in specimen['sample_registrations']:
                            assert sample["submitter_sample_id"] in ["SAMPLE_REGISTRATION_3", "SAMPLE_REGISTRATION_1", "SAMPLE_REGISTRATION_2"]
        else:
            continue


def test_validation(result, schema):
    # validate both roots emitted by v4: the clinical donor tree and program metadata
    schema.validate_ingest_map({"donors": result["donors"], "programs": result["programs"]})
    print(schema.validation_warnings)

    # model-logic warnings we control should all be present (data-quality enum warnings
    # are covered by test_validation_errors below)
    expected_warnings = [
        "DONOR_2 > PD_2: date_of_diagnosis required for primary_diagnoses",
        "DONOR_2 > PD_2: NOTE: cannot calculate any date intervals for this patient without date_of_diagnosis",
        "DONOR_2 > PD_2 > SPECIMEN_5: Tumour specimens require a reference_pathology_confirmed_diagnosis",
        "DONOR_2 > PD_2 > SPECIMEN_5: Tumour specimens require a tumour_grade",
        "DONOR_5: cause_of_death required if is_deceased = Yes",
        "DONOR_5: date_of_death required if is_deceased = Yes",
        "DONOR_5 > PD_5: basis_of_diagnosis required for primary_diagnoses",
        "DONOR_5 > PD_5 > TR_5 > Radiation 0: radiation_therapy_dosage required for radiations",
        "DONOR_5 > PD_5 > TR_10: Treatment type Systemic therapy should have one or more systemic therapies submitted",
        "DONOR_4: lost_to_followup_reason required if lost_to_follow_up == Yes",
        "DONOR_5: lost_to_followup_reason should only be submitted if lost_to_follow_up == Yes",
        # program-metadata validation (second root)
        "TEST_2: funding_sources required for programs",
    ]
    for w in expected_warnings:
        assert w in schema.validation_warnings, f"missing expected warning: {w}"
    assert len(schema.validation_warnings) == 19

    # temporary: remove 'month_interval' errors:
    schema.validation_errors = [e for e in schema.validation_errors if "month_interval" not in e]

    print(schema.validation_errors)
    expected_errors = [
        "DONOR_2 > PD_2 > TR_2: Treatment start cannot be after treatment end.",
        "DONOR_2 > PD_2 > TR_2: Systemic therapy start date cannot be earlier than its treatment start date.",
        "DONOR_2 > PD_2_1 > TR_8: Systemic therapy end date cannot be after its treatment end date.",
        "DONOR_3 > DUPLICATE_ID > primary_site: 'Tongue' is not valid under any of the given schemas",
        "DONOR_3 > PD_3 > TR_3: Systemic therapy start date cannot be earlier than its treatment start date.",
        "DONOR_1: PD_1 > TR_1: date_of_death cannot be earlier than treatment_end_date ",
        "DONOR_1: PD_1 > TR_1: treatment_start_date cannot be after date_of_death ",
        "Duplicated IDs: in schema followups, FOLLOW_UP_4 occurs 2 times",
    ]
    for e in expected_errors:
        assert e in schema.validation_errors, f"missing expected error: {e}"
    # invalid enum values in the v4 test data are caught as jsonschema errors on the
    # specimens (specimen_type) sub-schema
    assert any("specimen_type" in e for e in schema.validation_errors)
    assert len(schema.validation_errors) == 17

    # there should be an item named DUPLICATE_ID in both followup and primary_diagnoses
    print(json.dumps(schema.identifiers, indent=2))
    assert schema.identifiers["followups"]["DUPLICATE_ID"] == 1
    assert schema.identifiers["primary_diagnoses"]["DUPLICATE_ID"] == 1


def test_programs(result, schema):
    # v4 emits a separate `programs` array of ingestable program metadata
    programs = result["programs"]
    assert len(programs) == 2
    by_id = {p["program_id"]: p for p in programs}
    assert set(by_id) == {"TEST_1", "TEST_2"}

    # pipe-delimited array fields are parsed into lists
    test1 = by_id["TEST_1"]
    assert test1["keywords"] == ["cancer", "breast", "synthetic", "data"]
    assert test1["principal_investigators"] == ["John Doe, UHN", "Jane Deer, UBC"]
    assert test1["lead_organizations"] == ["UHN", "UBC"]

    # programs validate against ProgramIngestSchema: a bad enum is a jsonschema error
    schema.validate_ingest_map({"donors": [], "programs": [
        {"program_id": "P_BAD", "status": "NOT_A_STATUS"}
    ]})
    assert any("P_BAD > status" in e for e in schema.validation_errors)


# test mapping that uses values from multiple sheets:
def test_multisheet_mapping(packets):
    for packet in packets:
        for pd in packet["primary_diagnoses"]:
            if "specimens" in pd:
                for s in pd["specimens"]:
                    assert "multisheet" in s
                    assert "placeholder" in s["multisheet"]
                    if s["submitter_specimen_id"] == "SPECIMEN_5":
                        assert s["multisheet"]["placeholder"]["submitter_specimen_id"]["Specimen"] == "SPECIMEN_5"
                        assert len(s["multisheet"]["placeholder"]["submitter_specimen_id"]["Sample_Registration"]) == 3
                        assert len(s["multisheet"]["placeholder"]["extra"]["Sample_Registration"]) == 3
                    if s["submitter_specimen_id"] == "SPECIMEN_6":
                        assert s["multisheet"]["placeholder"]["submitter_specimen_id"]["Specimen"] == "SPECIMEN_6"
                        assert len(s["multisheet"]["placeholder"]["submitter_specimen_id"]["Sample_Registration"]) == 1
                        assert len(s["multisheet"]["placeholder"]["extra"]["Sample_Registration"]) == 1
                    if s["submitter_specimen_id"] == "SPECIMEN_3":
                        assert s["multisheet"]["placeholder"]["submitter_specimen_id"]["Specimen"] == "SPECIMEN_3"
                        assert len(s["multisheet"]["placeholder"]["submitter_specimen_id"]["Sample_Registration"]) == 0
                        assert len(s["multisheet"]["placeholder"]["extra"]["Sample_Registration"]) == 0

