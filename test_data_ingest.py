import pytest
import yaml
import CSVConvert
import mappings
import mohschema

# read sheet from given data pathway
raw_csvs, output_file = CSVConvert.ingest_raw_data("test_data/pytest_data", [])
mappings.IDENTIFIER_FIELD =  "Subject"
mappings.INDEXED_DATA = CSVConvert.process_data(raw_csvs)
mappings._push_to_stack(None, None, mappings.IDENTIFIER)

def test_single_val():
    mappings.IDENTIFIER = "ABC-01-03"
    test = CSVConvert.eval_mapping("{single_val(Treatment.THER_TX_NAME)}", None)
    assert test == "IRINOTECAN,IRINOTECAN"


def test_date():
    mappings.IDENTIFIER = "ABC-01-03"
    test = CSVConvert.eval_mapping("{single_date(Demographics.DTH_DT_RAW)}", None)
    assert test == "2023-09"


def test_list_val():
    mappings.IDENTIFIER = "ABC-01-05"
    test = CSVConvert.eval_mapping("{list_val(Demographics.DTH_DT_RAW)}", None)
    assert len(test) == 1

    mappings.IDENTIFIER = "ABC-01-03"
    test = CSVConvert.eval_mapping("{list_val(Treatment.THER_TX_NAME)}", None)
    assert test == ['IRINOTECAN,IRINOTECAN', 'IRINOTECAN,IRINOTECAN']

    mappings.IDENTIFIER = "ABC-01-03"
    test = CSVConvert.eval_mapping("{flat_list_val(Treatment.THER_TX_NAME)}", None)
    assert test == ['IRINOTECAN', 'IRINOTECAN', 'IRINOTECAN', 'IRINOTECAN']


@pytest.fixture
def schema():
    manifest_file = "test_data/manifest.yml"
    with open(manifest_file, 'r') as f:
        manifest = yaml.safe_load(f)
    if manifest is not None:
        return mohschema.mohschema(manifest['schema'])
    return None


@pytest.fixture
def packets():
    input_path = "test_data/raw_data"
    manifest_file = "test_data/manifest.yml"
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


def test_donor_6(packets, schema):
    for packet in packets:
        if packet['submitter_donor_id'] == "DONOR_6":
            for pd in packet['primary_diagnoses']:
                schema.validate_primary_diagnosis(pd)
                print(mohschema.VALIDATION_MESSAGES)
                assert "submitter_specimen_id SPECIMEN_43 does not correspond to one of the available specimen_ids" in ",".join(mohschema.VALIDATION_MESSAGES)
        else:
            continue
