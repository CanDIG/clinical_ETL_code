import CSVConvert

# read sheet from given data pathway
raw_csvs, output_file = CSVConvert.ingest_raw_data("test_data/pytest_data_v2.xlsx", [])
indexed_data = CSVConvert.process_data(raw_csvs, "Subject")

def test_single_val():
    test = CSVConvert.eval_mapping("ABC-01-03", indexed_data, "{single_val(THER_TX_NAME)}")
    assert test == "IRINOTECAN,IRINOTECAN"


def test_date():
    test = CSVConvert.eval_mapping("ABC-01-03", indexed_data, "{single_date(DTH_DT_RAW)}")
    assert test == "2023-09-25"


def test_list_val():
    test = CSVConvert.eval_mapping("ABC-01-05", indexed_data, "{list_val(DTH_DT_RAW)}")
    assert len(test) == 2

    test = CSVConvert.eval_mapping("ABC-01-03", indexed_data, "{list_val(THER_TX_NAME)}")
    assert test == ['IRINOTECAN,IRINOTECAN', 'IRINOTECAN,IRINOTECAN']

    test = CSVConvert.eval_mapping("ABC-01-03", indexed_data, "{flat_list_val(THER_TX_NAME)}")
    assert test == ['IRINOTECAN', 'IRINOTECAN', 'IRINOTECAN', 'IRINOTECAN']


def test_multiple_sheet_val():
    test = CSVConvert.eval_mapping("ABC-01-04", indexed_data, "{single_val(Diagnosis.DTH_DT_RAW)}")
    assert test == '2024 OCT 25'

    test = CSVConvert.eval_mapping("ABC-01-04", indexed_data, "{list_val(DTH_DT_RAW)}")
    assert test == ['2024 OCT 25', '2023 SEP 25']
