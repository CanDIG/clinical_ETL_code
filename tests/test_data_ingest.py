import pytest
import yaml
import os
import sys
import json

from clinical_etl import CSVConvert
from clinical_etl import mappings
from clinical_etl.mohschemav3 import MoHSchemaV3

# read sheet from given data pathway
REPO_DIR = os.path.abspath(f"{os.path.dirname(os.path.realpath(__file__))}")

@pytest.fixture
def schema():
    manifest_file = f"{REPO_DIR}/manifest.yml"
    with open(manifest_file, 'r') as f:
        manifest = yaml.safe_load(f)
    if manifest is not None:
        return MoHSchemaV3(manifest['schema'])
    return None


@pytest.fixture
def packets():
    input_path = f"{REPO_DIR}/raw_data"
    manifest_file = f"{REPO_DIR}/manifest.yml"
    mappings.INDEX_STACK = []
    return_values = CSVConvert.csv_convert(input_path, manifest_file, verbose=False)
    return return_values[0]


def test_csv_convert(packets):
    # 6 original sample donors + 5 completeness fixtures (CMPLT_AF/BF/AM/BM/INC)
    # + 2 full-coverage fulsome donors (CMPLT_COV1/COV2)
    assert len(packets) == 13


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


def test_validation(packets, schema):
    # Scope validation to the original sample donors so the expected warning /
    # error lists below are unaffected by the CMPLT_* completeness fixtures.
    original_ids = {"DONOR_1", "DONOR_2", "DONOR_3", "DONOR_4", "DONOR_5", "DONOR_6"}
    original = [p for p in packets if p["submitter_donor_id"] in original_ids]
    schema.validate_ingest_map({"donors": original})
    print(schema.validation_warnings)
    warnings = [
        "DONOR_2 > PD_2: date_of_diagnosis required for primary_diagnoses",
        "DONOR_2 > PD_2: NOTE: cannot calculate any date intervals for this patient without date_of_diagnosis",
        "DONOR_3 > PD_3: basis_of_diagnosis required for primary_diagnoses",
        "DONOR_5: cause_of_death required if is_deceased = Yes",
        "DONOR_5: date_of_death required if is_deceased = Yes",
        "DONOR_5 > PD_5: basis_of_diagnosis required for primary_diagnoses",
        "DONOR_5 > PD_5: clinical_stage_group is required for clinical_tumour_staging_system Revised International staging system (R-ISS)",
        "DONOR_5 > PD_5 > TR_5 > Radiation 0: radiation_therapy_dosage required for radiations",
        "DONOR_5 > PD_5 > TR_10: Treatment type Systemic therapy should have one or more systemic therapies submitted",
    ]
    assert len(schema.validation_warnings) == 9
    assert (sorted(schema.validation_warnings) == sorted(warnings))

    
    # temporary: remove 'month_interval' errors:
    schema.validation_errors = [e for e in schema.validation_errors if "month_interval" not in e]    
    
    print(schema.validation_errors)
    errors = [
        "DONOR_2 > PD_2 > TR_2: Treatment start cannot be after treatment end.",
        "DONOR_2 > PD_2 > TR_2: Systemic therapy end date cannot be after its treatment end date.",
        "DONOR_2 > PD_2 > TR_2: Systemic therapy start date cannot be earlier than its treatment start date.",
        "DONOR_2 > PD_2 > TR_2: Systemic therapy end date cannot be after its treatment end date.",
        "DONOR_2 > PD_2_1 > TR_8: Systemic therapy end date cannot be after its treatment end date.",
        "DONOR_3 > DUPLICATE_ID > primary_site: 'Tongue' is not valid under any of the given schemas",
        "DONOR_3 > PD_3 > TR_3: Systemic therapy start date cannot be earlier than its treatment start date.",
        "DONOR_1: PD_1 > TR_1: date_of_death cannot be earlier than treatment_end_date ",
        "DONOR_1: PD_1 > TR_1: treatment_start_date cannot be after date_of_death ",
        "DONOR_5: lost_to_followup_after_clinical_event_identifier cannot be present if is_deceased = Yes",
        "Duplicated IDs: in schema followups, FOLLOW_UP_4 occurs 2 times"
    ]
    assert len(schema.validation_errors) == 11
    assert (sorted(schema.validation_errors) == sorted(errors))


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


# Per-donor tier/level completeness summary over the full cohort.
# The tests/raw_data fixtures include five CMPLT_* donors purpose-built to land
# in each summary bucket:
#   CMPLT_AF  -> Tier A, fulsome   CMPLT_BF  -> Tier B, fulsome
#   CMPLT_AM  -> Tier A, minimal   CMPLT_BM  -> Tier B, minimal
#   CMPLT_INC -> untiered (single normal DNA sample) -> incomplete
def test_completeness_summary(packets, schema):
    schema.validate_ingest_map({"donors": packets})
    summary = CSVConvert.summarize_completeness(schema.statistics["donor_completeness"])

    assert summary["total_donors"] == 13
    # each axis partitions all donors exactly once
    assert (summary["tier_a_min_clinical_complete"]
            + summary["tier_b_min_clinical_complete"]
            + summary["incomplete_min_donors"]) == 13
    assert (summary["tier_a_full_clinical_complete"]
            + summary["tier_b_full_clinical_complete"]
            + summary["incomplete_full_donors"]) == 13
    # the CMPLT_* donors populate each category (Tier A donors are not also
    # counted toward Tier B); original donors only add to the incomplete buckets
    assert summary["tier_a_min_clinical_complete"] == 3    # CMPLT_AF, CMPLT_AM, CMPLT_COV1
    assert summary["tier_b_min_clinical_complete"] == 3    # CMPLT_BF, CMPLT_BM, CMPLT_COV2
    assert summary["tier_a_full_clinical_complete"] == 2   # CMPLT_AF, CMPLT_COV1
    assert summary["tier_b_full_clinical_complete"] == 2   # CMPLT_BF, CMPLT_COV2
    assert summary["incomplete_min_donors"] >= 1           # CMPLT_INC (+ originals)
    assert summary["incomplete_full_donors"] >= 3          # CMPLT_AM, CMPLT_BM, CMPLT_INC (+ originals)


# CMPLT_COV1 / CMPLT_COV2 populate every object type in the model, with all
# required and conditionally-required fields filled, so they should come out
# fulsome complete. This guards against the required-field lists drifting out of
# sync with the model (a newly-required field would make these donors fail).
def test_full_object_coverage_donors_are_fulsome(packets, schema):
    schema.validate_ingest_map({"donors": packets})
    dc = schema.statistics["donor_completeness"]
    for donor_id in ("CMPLT_COV1", "CMPLT_COV2"):
        assert dc[donor_id]["fulsome_complete"] is True, dc[donor_id]["fulsome_unmet"]
        assert dc[donor_id]["fulsome_unmet"] == []

    cov = next(p for p in packets if p["submitter_donor_id"] == "CMPLT_COV1")
    # donor-level objects
    for key in ("primary_diagnoses", "followups", "biomarkers", "comorbidities", "exposures"):
        assert cov.get(key), f"CMPLT_COV1 missing {key}"
    pd = cov["primary_diagnoses"][0]
    assert pd.get("specimens") and pd["specimens"][0].get("sample_registrations")
    tr = pd["treatments"][0]
    for key in ("systemic_therapies", "radiations", "surgeries"):
        assert tr.get(key), f"CMPLT_COV1 treatment missing {key}"
