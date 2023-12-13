import pytest
import yaml
from clinical_etl import CSVConvert
from clinical_etl import mappings
import json
import os
from clinical_etl.mohschema import MoHSchema

# read sheet from given data pathway
REPO_DIR = os.path.abspath(f"{os.path.dirname(os.path.realpath(__file__))}")
@pytest.fixture
def schema():
    manifest_file = f"{REPO_DIR}/test_data/manifest.yml"
    with open(manifest_file, 'r') as f:
        manifest = yaml.safe_load(f)
    if manifest is not None:
        return MoHSchema(manifest['schema'])
    return None


@pytest.fixture
def packets():
    input_path = f"{REPO_DIR}/test_data/raw_data"
    manifest_file = f"{REPO_DIR}/test_data/manifest.yml"
    mappings.INDEX_STACK = []
    return CSVConvert.csv_convert(input_path, manifest_file, verbose=False)


def test_csv_convert(packets):
    # there are 6 donors
    assert len(packets) == 6


def test_donor_1(packets):
    for packet in packets:
        if packet['submitter_donor_id'] == "DONOR_1":
            # test Followups: FOLLOW_UP_2 is in TR_1, FOLLOW_UP_1 is in PD_1, FOLLOW_UP_3 and FOLLOW_UP_4 are in DONOR_1
            for pd in packet['primary_diagnoses']:
                if "followups" in pd:
                    for f in pd['followups']:
                        assert f['submitter_primary_diagnosis_id'] == pd['submitter_primary_diagnosis_id']
                        assert f['submitter_follow_up_id'] == "FOLLOW_UP_1"
                if "treatments" in pd:
                    for t in pd["treatments"]:
                        if "followups" in t:
                            for f in t['followups']:
                                assert f['submitter_treatment_id'] == t['submitter_treatment_id']
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
                if 'specimen' in pd:
                    for specimen in pd['specimens']:
                        assert specimen['submitter_primary_diagnosis_id'] == pd['submitter_primary_diagnosis_id']
                        if 'sample_registrations' in specimen:
                            for sample in specimen['sample_registrations']:
                                assert sample["submitter_specimen_id"] == specimen['submitter_specimen_id']
        else:
            continue


def test_validation(packets, schema):
    schema.validate_ingest_map({"donors": packets})
    print(schema.validation_warnings)
    assert len(schema.validation_warnings) == 6
    # should be the following 6 warnings:
    # DONOR_5: cause_of_death required if is_deceased = Yes
    # DONOR_5: date_of_death required if is_deceased = Yes
    # DONOR_5 > PD_5: clinical_stage_group is required for clinical_tumour_staging_system Revised International staging system (RISS)
    # DONOR_5 > PD_5 > SPECIMEN_6: Tumour specimens require a reference_pathology_confirmed_diagnosis
    # DONOR_5 > PD_5 > TR_5 > Radiation 1: reference_radiation_treatment_id required if radiation_boost = Yes
    # DONOR_5 > PD_5 > TR_10: treatment type Immunotherapy should have one or more immunotherapies submitted

    print(schema.validation_errors)
    assert len(schema.validation_errors) == 2
    # should be the following 2 errors:
    # DONOR_6 > PD_6 > TR_9 > Surgery 0: submitter_specimen_id SPECIMEN_43 does not correspond to one of the available specimen_ids ['SPECIMEN_3']
    # Duplicated IDs: in schema followups, FOLLOW_UP_4 occurs 2 times

    # there should be an item named DUPLICATE_ID in both followup and sample_registration
    print(json.dumps(schema.identifiers, indent=2))
    assert schema.identifiers["followups"]["DUPLICATE_ID"] == 1
    assert schema.identifiers["primary_diagnoses"]["DUPLICATE_ID"] == 1


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

