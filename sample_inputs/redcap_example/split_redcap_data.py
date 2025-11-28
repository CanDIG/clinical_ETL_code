"""
Methods to transform the redcap raw data into the csv format expected by
CSVConvert.py
"""

import os
import argparse
from pathlib import Path

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="""Directory containing raw 
        csv value and label exports from Redcap""",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tmp_out",
        help="Optional name of output directory in same directory as input; default tmp_out",
    )
    args = parser.parse_args()
    return args


def read_redcap_export(export_path):
    """Read exported redcap label and value csvs from the given input path.
    Assign column names."""
    files = [f for f in os.listdir(export_path) if ".csv" in f]
    value_file = [f for f in files if "value" in f]
    label_file = [f for f in files if "label" in f]
    assert (
        len(value_file) == 1 and len(label_file) == 1
    ), f"Missing value or label csv files in {export_path}. Check the file names include 'value' and 'label'"
    assert (
        len(value_file) < 2 or len(label_file) < 2
    ), f"There is more than one value or label csv file in {export_path}. Ensure there is only one of each."
    try:
        value_df = pd.read_csv(os.path.join(export_path, value_file[0]), dtype=str)
        label_df = pd.read_csv(os.path.join(export_path, label_file[0]), dtype=str)
    except Exception as e:
        raise Exception(f"File inputs do not seem to be valid csv files")
    label_df.columns = list(value_df.columns)
    label_df.dropna(how="all", axis=1, inplace=True)
    return label_df


def extract_repeat_instruments(df):
    """Transforms the single (very sparse) dataframe into one dataframe per
    MoH schema. This makes it easier to look at, and also eliminates a bunch
    of pandas warnings."""
    new_dfs = {}
    starting_rows = df.shape[0]
    repeat_instruments = df["redcap_repeat_instrument"].dropna().unique()
    total_rows = 0
    for i in repeat_instruments:
        # each row has a redcap_repeat_instrument that describes the schema
        # (e.g. Treatment) and a redcap_repeat_instance that is an id for that
        # schema (this would be the treatment.id)
        print(f"Extracting schema {i}")
        schema_df = df.loc[df["redcap_repeat_instrument"] == i]
        # drop all of the empty columns that aren't relevent for this schema
        schema_df = drop_empty_columns(schema_df)
        # rename the redcap_repeat_instance to the specific id (e.g. treatment_id)
        schema_df.rename(columns={"redcap_repeat_instance": f"{i}_id"}, inplace=True)
        total_rows += schema_df.shape[0]
        new_dfs[i] = schema_df

    # now save all of the rows that aren't a repeat_instrument and
    # label them Singleton for now
    singletons = df.loc[df["redcap_repeat_instrument"].isnull()]
    singletons = drop_empty_columns(singletons)
    # check that we have all of the rows
    if total_rows + singletons.shape[0] < starting_rows:
        print("Warning: not all rows recovered in raw data")
    new_dfs["Singleton"] = singletons
    return new_dfs


def split_singleton(new_dfs):
    """Split singleton df into donor, primary diagnois and exposures."""
    columns = {
        "Donor": [
            "program_id",
            "submitter_donor_id",
            "sex_at_birth",
            "is_deceased",
            "cause_of_death",
            "date_of_birth",
            "date_of_death",
            "lost_to_followup",
            "lost_to_followup_reason",
            "date_alive_after_lost_to_followup",
            "lost_to_followup_after_clinical_event_identifier",
        ],
        "Primary Diagnosis": [
            "submitter_donor_id",
            "submitter_primary_diagnosis_id",
            "date_of_diagnosis",
            "primary_site",
            "cancer_type_code",
            "basis_of_diagnosis",
            "laterality",
            "clinical_t_category",
            "clinical_n_category",
            "clinical_m_category",
            "clinical_stage_group",
            "t_category_clin",  # These names
            "n_category_clin",  # are used in
            "m_category_clin",  # redcap template
            "pathological_t_category",
            "pathological_n_category",
            "pathological_m_category",
            "pathological_stage_group",
            "lymph_nodes_examined_status",  # These three
            "lymph_nodes_examined_method",  # were removed
            "number_lymph_nodes_positive",  # in MoH model 3.0
        ],
        "Exposures": [
            "submitter_donor_id",
            "tobacco_smoking_status",
            "tobacco_type",
            "years_smoking",
            "r_years_smoking",  # redcap template name
            "pack_years_smoked",
        ],
    }
    # Remove columns not in template
    for table, cols in columns.items():
        cols = [col for col in cols if col in new_dfs["Singleton"].columns]
        columns.update({table: cols})
    new_dfs["Donor"] = new_dfs["Singleton"][columns["Donor"]]
    new_dfs["Primary Diagnosis"] = new_dfs["Singleton"][columns["Primary Diagnosis"]]
    new_dfs["Exposures"] = new_dfs["Singleton"][columns["Exposures"]]
    del new_dfs["Singleton"]
    return new_dfs


def drop_empty_columns(df):
    empty_cols = [col for col in df if df[col].isnull().all()]
    df = df.drop(empty_cols, axis=1)
    return df


def output_dfs(input_path, output_dir, df_list):
    parent_path = Path(input_path).parent
    tmpdir = Path(parent_path, output_dir)
    if not tmpdir.is_dir():
        tmpdir.mkdir()
    print(f"Writing output files to {tmpdir}")
    for d in df_list:
        df_list[d].to_csv(Path(tmpdir, f"{d}.csv"), index=False)


def main(args):
    input_path = args.input
    redcap_df = read_redcap_export(input_path)
    new_dfs = extract_repeat_instruments(redcap_df)
    new_dfs = split_singleton(new_dfs)
    output_dir = args.output
    output_dfs(input_path, output_dir, new_dfs)


if __name__ == "__main__":
    main(parse_args())
