from candigETL.convert import CSVConvert
from candigETL.mapping import mappings

# read sheet from given data pathway
raw_csvs, output_file = CSVConvert.ingest_raw_data("test_data/pytest_data_v2.xlsx", [])
mappings.IDENTIFIER_FIELD =  "Subject"
mappings.INDEXED_DATA = CSVConvert.process_data(raw_csvs)
mappings.push_to_stack(None, None, mappings.IDENTIFIER)

def test_single_val():
    mappings.IDENTIFIER = "ABC-01-03"
    test = CSVConvert.eval_mapping(mappings.IDENTIFIER, "{single_val(THER_TX_NAME)}", None, None)
    assert test == "IRINOTECAN,IRINOTECAN"


def test_date():
    mappings.IDENTIFIER = "ABC-01-03"
    test = CSVConvert.eval_mapping(mappings.IDENTIFIER, "{single_date(DTH_DT_RAW)}", None, None)
    assert test == "2023-09-25"


def test_list_val():
    mappings.IDENTIFIER = "ABC-01-05"
    test = CSVConvert.eval_mapping(mappings.IDENTIFIER, "{list_val(DTH_DT_RAW)}", None, None)
    assert len(test) == 2

    mappings.IDENTIFIER = "ABC-01-03"
    test = CSVConvert.eval_mapping(mappings.IDENTIFIER, "{list_val(THER_TX_NAME)}", None, None)
    assert test == ['IRINOTECAN,IRINOTECAN', 'IRINOTECAN,IRINOTECAN']

    mappings.IDENTIFIER = "ABC-01-03"
    test = CSVConvert.eval_mapping(mappings.IDENTIFIER, "{flat_list_val(THER_TX_NAME)}", None, None)
    assert test == ['IRINOTECAN', 'IRINOTECAN', 'IRINOTECAN', 'IRINOTECAN']


def test_multiple_sheet_val():
    mappings.IDENTIFIER = "ABC-01-04"
    test = CSVConvert.eval_mapping(mappings.IDENTIFIER, "{single_val(Diagnosis.DTH_DT_RAW)}", None, None)
    assert test == '2024 OCT 25'

    mappings.IDENTIFIER = "ABC-01-04"
    test = CSVConvert.eval_mapping(mappings.IDENTIFIER, "{list_val(DTH_DT_RAW)}", None, None)
    assert test == ['2024 OCT 25', '2023 SEP 25']
