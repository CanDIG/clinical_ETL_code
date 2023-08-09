import CSVConvert
import mappings

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


