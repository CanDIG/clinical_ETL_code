import pytest

from clinical_etl import mappings


@pytest.mark.parametrize(
    "data_values, reference, format, expected",
    [
        (
            {"date_of_birth": {"Donor": "5/1/1995"}},
            {"offset": "2018-05-01", "period": "month"},
            "MDY",
            {"month_interval": -276},
        ),
        (
            {"date_of_birth": {"Donor": "5/1/1995"}},
            {"offset": "2018-05-01", "period": "day"},
            "MDY",
            {"day_interval": -8401, "month_interval": -276},
        ),
        (
            {"date_of_birth": {"Donor": "1/5/1995"}},
            {"offset": "2018-05-01", "period": "month"},
            "DMY",
            {"month_interval": -276},
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
            {"date_of_birth": {"Donor": "5/1/1995"}},
            {"offset": "2018-05-01", "period": "month"},
            "MDY",
            {"month_interval": -276},
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
        # TODO: exception when date doesn't match date order
    ],
)
def test_date_intervals(data_values, reference, format, expected):
    assert mappings.date_interval(data_values, reference, format) == expected