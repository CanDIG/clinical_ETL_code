import pytest

from clinical_etl.mappings import _date_interval, MappingError


@pytest.mark.parametrize(
    "data_values, reference, date_format, expected",
    [
        (
            {"date_of_birth": {"Donor": "5/2/2016"}},
            {"offset": "2018-05-01", "period": "month"},
            "MDY",
            {"month_interval": -23},
        ),
        (
            {"date_of_birth": {"Donor": "5/2/2016"}},
            {"offset": "2018-05-01", "period": "day"},
            "MDY",
            {"day_interval": -729, "month_interval": -23},
        ),
        (
            {"date_of_birth": {"Donor": "2/5/2016"}},
            {"offset": "2018-05-01", "period": "month"},
            "DMY",
            {"month_interval": -23},
        ),
        (
            {"date_of_diagnosis": {"PrimaryDiagnosis": "1/5/2018"}},
            {"offset": "2018-05-01", "period": "month"},
            "DMY",
            {"month_interval": 0},
        ),
        (
            {"date_of_diagnosis": {"PrimaryDiagnosis": "1/5/2018"}},
            {"offset": "2018-05-01", "period": "day"},
            "DMY",
            {"day_interval": 0, "month_interval": 0},
        ),
        (
            {"date_of_diagnosis": {"PrimaryDiagnosis": "5/1/2018"}},
            {"offset": "2018-05-01", "period": "month"},
            "MDY",
            {"month_interval": 0},
        ),
        (
            {"date_of_diagnosis": {"PrimaryDiagnosis": "2018-05-01"}},
            {"offset": "2018-05-01", "period": "month"},
            "YMD",
            {"month_interval": 0},
        ),
        (
            {"date_of_birth": {"Donor": "5/2/2016"}},
            {"offset": "2018-05-01", "period": "month"},
            "MDY",
            {"month_interval": -23},
        ),
        (
            {"specimen_collection_date": {"Specimens": "5/1/2021"}},
            {"offset": "2018-05-01", "period": "month"},
            "MDY",
            {"month_interval": 36},
        ),
        (
            {"specimen_collection_date": {"Specimens": "5/1/2021"}},
            {"offset": "2018-05-01", "period": "day"},
            "MDY",
            {"day_interval": 1096, "month_interval": 36},
        ),
        (
            {"specimen_collection_date": {"Specimens": "1/5/2021"}},
            {"offset": "2018-05-01", "period": "month"},
            "DMY",
            {"month_interval": 36},
        ),
        (
            {"specimen_collection_date": {"Specimens": "2021/5/1"}},
            {"offset": "2018-05-01", "period": "month"},
            "YMD",
            {"month_interval": 36},
        ),
        (
            {"specimen_collection_date": {"Specimens": "2021/5"}},
            {"offset": "2018-05-01", "period": "month"},
            "YMD",
            {"month_interval": 36},
        ),
        (
            {"specimen_collection_date": {"Specimens": "5/2021"}},
            {"offset": "2018-05-01", "period": "month"},
            "MYD",
            {"month_interval": 36},
        ),
        (
            {"specimen_collection_date": {"Specimens": "2021"}},
            {"offset": "2018-05-01", "period": "month"},
            "MYD",
            {"month_interval": 32},  # Picks the first month of the year
        ),
    ],
)
def test_valid_date_intervals(data_values, reference, date_format, expected):
    print("data_values:", data_values)
    print("reference:", reference)
    print("interval:", _date_interval(data_values, reference, date_format))
    assert _date_interval(data_values, reference, date_format) == expected


@pytest.mark.parametrize(
    "data_values, reference, date_format, expected",
    [
        (
            {"date_of_birth": {"Donor": "15/1/1995"}},
            {"offset": "2018-05-01", "period": "month"},
            "MDY",
            pytest.raises(MappingError),
        ),
        (
            {"date_of_birth": {"Donor": "5 1 1995"}},
            {"offset": "2018-05-01", "period": "day"},
            "MDY",
            pytest.raises(MappingError),
        ),
        (
            {"date_of_birth": {"Donor": "1,5,1995"}},
            {"offset": "2018-05-01", "period": "month"},
            "DMY",
            pytest.raises(MappingError),
        ),
        (
            {"date_of_diagnosis": {"PrimaryDiagnosis": "41/5/2018"}},
            {"offset": "2018-05-01", "period": "month"},
            "DMY",
            pytest.raises(MappingError),
        ),
        (
            {"date_of_diagnosis": {"PrimaryDiagnosis": "1/5/2018"}},
            {"offset": "2018-05-01", "period": "day"},
            "YMD",
            pytest.raises(MappingError),
        ),
        (
            {"specimen_collection_date": {"Specimens": "2021/5"}},
            {"offset": "2018-05-15", "period": "month"},
            "MYD",
            pytest.raises(MappingError),
        ),
        (
            {"specimen_collection_date": {"Specimens": "21"}},
            {"offset": "2018-05-15", "period": "month"},
            "MYD",
            pytest.raises(MappingError),
        ),
    ],
)
def test_invalid_date_intervals(data_values, reference, date_format, expected):
    with expected as e:
        assert _date_interval(data_values, reference, date_format) == e
