"""
Methods to transform the redcap raw data into the csv format expected by
CSVConvert.py
"""

import os
import argparse
import re
import pandas
import json
from pathlib import Path
import sys
import pprint
import dateparser
import clinical_etl.mappings as mp
from clinical_etl.mappings import MappingError
import copy

import pandas as pd
pd.options.mode.chained_assignment = None


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True, help="Path to raw csv output from Redcap")
    parser.add_argument('--labels', type=str, required=False, help="Path to labels csv output from Redcap if present")
    parser.add_argument('--verbose', '--v', action="store_true", help="Print extra information")
    parser.add_argument('--output', type=str, default="tmp_out",
                        help="Optional name of output directory in same directory as input; default tmp_out")
    parser.add_argument('--error-dates', type=str, required=False,
                        help="Path to a file that contains information about invalid dates that need to be cleaned")
    args = parser.parse_args()
    return args


def read_csv(input_path, labels_path):
    print(f"Reading input file {input_path}")
    try:
        input_csv = pd.read_csv(input_path, dtype=str, encoding="latin-1")
        labels_csv = pd.read_csv(labels_path, dtype=str, encoding="latin-1")
    except Exception as e:
        print(e)
        print(f"File inputs does not seem to be a valid csv file")
        sys.exit()
    labels_csv.columns = list(input_csv.columns)
    labels_csv.dropna(how='all', axis=1, inplace=True)
    return labels_csv


def melt_dataframe(dataframe, id_vars: list, prefixes: list):
    """
    For schemas that have repeating wide instruments, merge them into a long df
    """
    max_digit = max(set(re.findall(r'(\d+)', ' '.join(dataframe.columns.values))))
    df_list = []
    for i in range(1, int(max_digit)):
        numbered_columns = [s + f"_{str(i)}" for s in prefixes]
        filtered_columns = list(set(numbered_columns).intersection(set(dataframe.columns.values)))
        columns_to_select = id_vars + filtered_columns
        selected_df = dataframe[columns_to_select]
        selected_df.dropna(subset=filtered_columns, how='all', axis=0, inplace=True)
        selected_df.columns = selected_df.columns.str.replace(f'_{i}', '')
        df_list.append(selected_df)
    df_long = pd.concat(df_list)
    return df_long


def fix_dates(date: str):
    """
    Replace Unk values with values advised in the curation guidelines,
    no month = 6, no day = 15, no year, None
    """
    if pd.isnull(date) or date == "Unknown":
        return None
    split_date = date.split("-")
    if len(split_date) < 3:
        print(date)
    if split_date[0] == "Unk":
        return None
    if split_date[1] == "Unk":
        #split_date[1] = "06"
        return None
    if split_date[2] == "Unk":
        split_date[2] = "15"
    joined_date = "-".join(split_date)
    try:
        mp._validate_date_format(joined_date, 'YMD')
        return joined_date
    except MappingError as e:
        try:
            mp._validate_date_format(date, 'DMY')
            parsed_date = dateparser.parse(date, settings={"PREFER_DAY_OF_MONTH": "first", "DATE_ORDER": 'DMY'})
            return parsed_date.strftime("%Y-%m-%d")
        except MappingError as e:
            print(e)
            return None


def censor_drug_names(drug_name):
    drug_allow_list = ["atezolizumab",
                       "autologous stem cell transplant",
                       "bevacizumab",
                       "bortezomib",
                       "cabozantinib",
                       "capecitabine",
                       "carboplatin",
                       "cetuximab",
                       "cisplatin",
                       "cyclophosphamide",
                       "dexamethasone",
                       "docetaxel",
                       "doxorubicin",
                       "durvalumab",
                       "epirubicin",
                       "eribulin",
                       "erlotinib",
                       "etoposide",
                       "fluorouracil",
                       "gemcitabine",
                       "irinotecan",
                       "ixazomib",
                       "lenalidomide",
                       "lenvatinib",
                       "leucovorin calcium",
                       "methotrexate",
                       "nivolumab",
                       "olaparib",
                       "oxaliplatin",
                       "paclitaxel",
                       "paclitaxel protein-bound",
                       "pazopanib",
                       "pembrolizumab",
                       "platinum",
                       "prednisolone",
                       "rituximab",
                       "tandem autologous stem cell transplant",
                       "vincristine"]
    if drug_name in drug_allow_list:
        return drug_name
    else:
        return "Investigational agent"


def remove_problem_dates(data_df_list, error_dates_df_path):
    error_dates_df = pd.read_csv(error_dates_df_path)
    error_dates_df['tx_idx'] = error_dates_df.groupby('treatment_id').cumcount()
    error_dates = error_dates_df.to_dict(orient="records")
    treatment_df = copy.deepcopy(data_df_list['treatment_new'])
    donor_df = copy.deepcopy(data_df_list['singleton'])
    systemic_therapy_df = copy.deepcopy(data_df_list['systemic_therapy'])
    for v_error in error_dates:
        if v_error['reason'].strip() == "TreatmentStart cannot be after treatment end.":
            treatment_df.loc[treatment_df['submitter_treatment_id'] == v_error['treatment_id'].strip(),
            ['treatment_start_date', 'treatment_end_date']] = None
        elif v_error['reason'].strip() == "date_of_death cannot be earlier than treatment_end_date":
            treatment_df.loc[
                treatment_df['submitter_treatment_id'] == str(v_error['treatment_id']).strip(), ['treatment_end_date']] = None
        elif v_error['reason'].strip() == "Treatment_start_date cannot be after date_of_death":
            treatment_df.loc[
                treatment_df['submitter_treatment_id'] == v_error['treatment_id'].strip(),
                ['treatment_start_date']] = None
        elif v_error['reason'].strip() == "Systemic therapyStart cannot be afterSystemic therapy end.":
            systemic_therapy_df.loc[systemic_therapy_df['submitter_treatment_id'] ==
                                    v_error['treatment_id'].strip(), ['start_date', 'end_date']] = None
        elif v_error['reason'].strip() == "date_of_birth cannot be later than date_of_diagnosis":
            donor_df.loc[donor_df['submitter_donor_id'] == v_error['donor_id'].strip(), ['date_of_death']] = None
        elif v_error['reason'].strip() == "Treatment_start_date cannot be before date_of_birth":
            donor_df.loc[donor_df['submitter_donor_id'] == v_error['donor_id'].strip(), ['date_of_birth']] = None
        else:
            pprint.pprint(v_error)
            print("No method found to fix this error, review errors and revise method")
    data_df_list['treatment_new'] = treatment_df
    data_df_list['singleton'] = donor_df
    data_df_list['systemic_therapy'] = systemic_therapy_df
    return data_df_list


def extract_repeat_instruments(df):
    """ Transforms the single (very sparse) dataframe into one dataframe per
    MoH schema. This makes it easier to look at, and also eliminates a bunch
    of pandas warnings."""
    new_dfs = {}
    starting_rows = df.shape[0]

    repeat_instruments = df['redcap_repeat_instrument'].unique()
    print(repeat_instruments)
    total_rows = 0
    for i in repeat_instruments:
        # each row has a redcap_repeat_instrument that describes the schema
        # (e.g. Treatment) and a redcap_repeat_instance that is an id for that
        # schema (this would be the treatment.id)
        if str(i) == "nan":
            i = "singleton"
        print(f"\n\nExtracting schema {i}")
        schema_df = df.loc[df['redcap_repeat_instrument'] == i]
        # drop all of the empty columns that aren't relevant for this schema
        schema_df.dropna(how='all', axis=1, inplace=True)
        # rename the redcap_repeat_instance to the specific id (e.g. treatment_id)
        schema_df.rename(columns={
            'redcap_repeat_instance': f"{i}_id"
            },
            inplace=True)
        total_rows += schema_df.shape[0]
        # replace any unknown date values
        date_columns = list(schema_df.filter(regex="(date$)|(^date.*(?<!(_d|_m|_y))$)|(date_[0-9]*$)").columns.values)
        if len(date_columns) > 0:
            schema_df[date_columns] = schema_df[date_columns].map(lambda x: fix_dates(x))
        if i.lower() == "specimen":
            schema_df.rename(columns={"submitter_primary_diagnosis_id_specimen": "submitter_primary_diagnosis_id"},
                             inplace=True)
        if i.lower() == "sample registration":
            schema_df.rename(columns={"submitter_specimen_id_sample_registration": "submitter_specimen_id"},
                             inplace=True)
        if i.lower() == "treatment":
            schema_df.rename(columns={"submitter_primary_diagnosis_id_treatment": "submitter_primary_diagnosis_id"},
                             inplace=True)
        if i.lower() == "follow up":
            schema_df.rename(columns={"submitter_primary_diagnosis_id_follow_up": "submitter_primary_diagnosis_id"},
                             inplace=True)
        if i.lower() == "biomarker":
            schema_df.rename(columns={"submitter_primary_diagnosis_id_biomarker": "submitter_primary_diagnosis_id"},
                             inplace=True)
        new_dfs[i] = schema_df

    # now save all of the rows that aren't a repeat_instrument and
    # label them Singleton for now
    singletons = df.loc[df['redcap_repeat_instrument'].isnull()]
    singletons.dropna(how='all', axis=1, inplace=True)
    date_columns = list(singletons.filter(regex="(date$)|(^date.*(?<!(_d|_m|_y))$)").columns.values)
    if len(date_columns) > 0:
        singletons[date_columns] = singletons[date_columns].map(lambda x: fix_dates(x))
    # check that we have all of the rows
    if total_rows + singletons.shape[0] < starting_rows:
        print("Warning: not all rows recovered in raw data")
    singletons['date_resolution'] = "day"
    new_dfs['singleton'] = singletons

    # define the columns for each treatment type
    treatment_id_vars = ["submitter_donor_id",
                         "redcap_repeat_instrument",
                         "Treatment_id",
                         "redcap_data_access_group",
                         "program_id_treatment",
                         "submitter_treatment_id",
                         "treatment_start_date",
                         "treatment_end_date"]

    treatment_columns = ["submitter_donor_id",
                         "redcap_repeat_instrument",
                         "Treatment_id",
                         "redcap_data_access_group",
                         "program_id_treatment",
                         "submitter_primary_diagnosis_id",
                         "submitter_treatment_id",
                         "treatment_type",
                         "is_primary_treatment",
                         "treatment_start_date_y",
                         "treatment_start_date_m",
                         "treatment_start_date_d",
                         "treatment_start_date",
                         "treatment_end_date_y",
                         "treatment_end_date_m",
                         "treatment_end_date_d",
                         "treatment_end_date",
                         "treatment_intent",
                         "response_to_treatment_criteria_method",
                         "response_to_treatment",
                         "status_of_treatment"]
    keep_treatment_columns = list(set(treatment_columns).intersection(set(new_dfs['Treatment'].columns.values)))

    surgery_columns = treatment_id_vars + [
        "surgery_reference_database_1",
        "surgery_reference_identifier_1",
        "surgery_type_1",
        "surgery_site_1",
        "surgery_location_1",
        "tumour_length_1",
        "tumour_width_1",
        "greatest_dimension_tumour_1",
        "tumour_focality_1",
        "residual_tumour_classification_1",
        "margin_types_involved_1",
        "margin_types_not_assessed_1",
        "lymphovascular_invasion_1",
        "perineural_invasion_1",
        "surgery_reference_database_2",
        "surgery_reference_identifier_2",
        "surgery_type_2",
        "surgery_site_2",
        "surgery_location_2",
        "tumour_length_2",
        "tumour_width_2",
        "greatest_dimension_tumour_2",
        "tumour_focality_2",
        "lymphovascular_invasion_2",
        "perineural_invasion_2",
        "surgery_reference_database_3",
        "surgery_reference_identifier_3",
        "surgery_type_3",
        "surgery_site_3",
        "surgery_location_3",
        "tumour_length_3",
        "tumour_width_3",
        "greatest_dimension_tumour_3",
        "tumour_focality_3",
        "lymphovascular_invasion_3",
        "perineural_invasion_3",
        "surgery_reference_database_4",
        "surgery_reference_identifier_4",
        "surgery_type_4",
        "surgery_site_4",
        "surgery_location_4",
        "tumour_length_4",
        "tumour_width_4",
        "greatest_dimension_tumour_4",
        "tumour_focality_4",
        "lymphovascular_invasion_4",
        "perineural_invasion_4",
        "surgery_reference_database_5",
        "surgery_reference_identifier_5",
        "surgery_type_5",
        "surgery_site_5",
        "surgery_location_5",
        "tumour_length_5",
        "tumour_width_5",
        "greatest_dimension_tumour_5",
        "tumour_focality_5",
        "lymphovascular_invasion_5",
        "perineural_invasion_5",
        "surgery_reference_database_6",
        "surgery_reference_identifier_6",
        "surgery_type_6",
        "surgery_site_6",
        "surgery_location_6",
        "greatest_dimension_tumour_6",
        "tumour_focality_6",
        "lymphovascular_invasion_6",
        "perineural_invasion_6",
        "surgery_reference_database_7",
        "surgery_reference_identifier_7",
        "surgery_type_7",
        "surgery_site_7",
        "surgery_location_7",
        "greatest_dimension_tumour_7",
        "tumour_focality_7",
        "lymphovascular_invasion_7",
        "perineural_invasion_7"]
    keep_surgery_columns = list(set(surgery_columns).intersection(set(new_dfs['Treatment'].columns.values)))
    surgery_prefixes = ['surgery_reference_database', 'surgery_reference_identifier', 'surgery_type', 'surgery_site',
                        'surgery_location', 'tumour_length', 'tumour_width', 'greatest_dimension_tumour',
                        'tumour_focality', 'residual_tumour_classification', 'margin_types_involved',
                        'margin_types_not_assessed', 'lymphovascular_invasion', 'perineural_invasion']

    systemic_therapy_columns = treatment_id_vars + [
        "systemic_therapy_type_1",
        "start_date_y_1",
        "start_date_m_1",
        "start_date_d_1",
        "start_date_1",
        "end_date_y_1",
        "end_date_m_1",
        "end_date_d_1",
        "end_date_1",
        "drug_reference_database_1",
        "drug_reference_identifier_1",
        "drug_name_1",
        "drug_dose_units_1",
        "days_per_cycle_1",
        "number_of_cycles_1",
        "prescribed_cumulative_drug_dose_1",
        "actual_cumulative_drug_dose_1",
        "systemic_therapy_type_2",
        "start_date_y_2",
        "start_date_m_2",
        "start_date_d_2",
        "start_date_2",
        "end_date_y_2",
        "end_date_m_2",
        "end_date_d_2",
        "end_date_2",
        "drug_reference_database_2",
        "drug_reference_identifier_2",
        "drug_name_2",
        "drug_dose_units_2",
        "days_per_cycle_2",
        "number_of_cycles_2",
        "prescribed_cumulative_drug_dose_2",
        "actual_cumulative_drug_dose_2",
        "systemic_therapy_type_3",
        "start_date_y_3",
        "start_date_m_3",
        "start_date_d_3",
        "start_date_3",
        "end_date_y_3",
        "end_date_m_3",
        "end_date_d_3",
        "end_date_3",
        "drug_reference_database_3",
        "drug_reference_identifier_3",
        "drug_name_3",
        "drug_dose_units_3",
        "days_per_cycle_3",
        "number_of_cycles_3",
        "prescribed_cumulative_drug_dose_3",
        "actual_cumulative_drug_dose_3",
        "systemic_therapy_type_4",
        "start_date_y_4",
        "start_date_m_4",
        "start_date_d_4",
        "start_date_4",
        "end_date_y_4",
        "end_date_m_4",
        "end_date_d_4",
        "end_date_4",
        "drug_reference_database_4",
        "drug_reference_identifier_4",
        "drug_name_4",
        "days_per_cycle_4",
        "number_of_cycles_4",
        "actual_cumulative_drug_dose_4",
        "systemic_therapy_type_5",
        "start_date_y_5",
        "start_date_m_5",
        "start_date_d_5",
        "start_date_5",
        "end_date_y_5",
        "end_date_m_5",
        "end_date_d_5",
        "end_date_5",
        "drug_reference_database_5",
        "drug_reference_identifier_5",
        "drug_name_5",
        "days_per_cycle_5",
        "number_of_cycles_5",
        "systemic_therapy_type_6",
        "start_date_y_6",
        "start_date_m_6",
        "start_date_d_6",
        "start_date_6",
        "end_date_y_6",
        "end_date_m_6",
        "end_date_d_6",
        "end_date_6",
        "drug_reference_database_6",
        "drug_reference_identifier_6",
        "drug_name_6",
        "days_per_cycle_6",
        "number_of_cycles_6",
        "systemic_therapy_type_7",
        "start_date_y_7",
        "start_date_m_7",
        "start_date_d_7",
        "start_date_7",
        "end_date_y_7",
        "end_date_m_7",
        "end_date_d_7",
        "end_date_7",
        "drug_name_7",
        "systemic_therapy_type_8",
        "start_date_y_8",
        "start_date_m_8",
        "start_date_d_8",
        "start_date_8",
        "end_date_y_8",
        "end_date_m_8",
        "end_date_d_8",
        "end_date_8",
        "systemic_therapy_type_9",
        "start_date_y_9",
        "start_date_m_9",
        "start_date_d_9",
        "start_date_9",
        "end_date_y_9",
        "end_date_m_9",
        "end_date_d_9",
        "end_date_9"]
    keep_systemic_therapy_columns = list(
        set(systemic_therapy_columns).intersection(set(new_dfs['Treatment'].columns.values)))
    systemic_therapy_prefixes = [
        "systemic_therapy_type",
        "start_date_y",
        "start_date_m",
        "start_date_d",
        "start_date",
        "end_date_y",
        "end_date_m",
        "end_date_d",
        "end_date",
        "drug_reference_database",
        "drug_reference_identifier",
        "drug_name",
        "drug_dose_units",
        "days_per_cycle",
        "number_of_cycles",
        "prescribed_cumulative_drug_dose",
        "actual_cumulative_drug_dose"
    ]

    radiation_columns = treatment_id_vars + [
        "radiation_therapy_modality",
        "radiation_therapy_type",
        "radiation_therapy_fractions",
        "radiation_therapy_dosage",
        "anatomical_site_irradiated",
        "anatomical_site_irradiated_other",
        "radiation_boost",
        "reference_radiation_treatment_id"]
    keep_radiation_columns = list(set(radiation_columns).intersection(set(new_dfs['Treatment'].columns.values)))

    # Get the intersection between remaining columns for each treatment type

    new_dfs['treatment_new'] = new_dfs['Treatment'][keep_treatment_columns]
    new_dfs['surgery'] = melt_dataframe(new_dfs['Treatment'][keep_surgery_columns], treatment_id_vars, surgery_prefixes)
    st_df = melt_dataframe(new_dfs['Treatment'][keep_systemic_therapy_columns], treatment_id_vars,
                           systemic_therapy_prefixes)
    st_df['drug_name'] = st_df['drug_name'].map(lambda x: censor_drug_names(x))
    st_df.loc[st_df['drug_name'] == "Investigational agent", ['drug_reference_identifier', 'drug_reference_database']] = None
    new_dfs['systemic_therapy'] = st_df

    new_dfs['radiation'] = new_dfs['Treatment'][keep_radiation_columns]
    del new_dfs['Treatment']
    return new_dfs


def make_output_dir(input_path, output_dir):
    parent_path = Path(input_path).parent
    tmpdir = Path(parent_path, output_dir)
    if not tmpdir.is_dir():
        tmpdir.mkdir()
    return tmpdir


def output_dfs(tmpdir: Path, df_dict: dict):
    print(f"Writing output files to {tmpdir}")
    columns_dict = {}
    for k, v in df_dict.items():
        print(k)
        columns_dict[k] = list(v.columns.values)
        filename = k.replace(" ", "_")
        filename = filename.lower()
        v.to_csv(Path(tmpdir, f"{filename}.csv"), index=False)
    with open(Path(tmpdir, "column_headers.json"), "w+") as f:
        json.dump(columns_dict, f, indent=4)


def main(args):
    input_path = args.input
    output_dir = args.output
    output_dir = make_output_dir(input_path, output_dir)
    if args.labels:
        redcap_csv = read_csv(args.input, args.labels)
    else:
        redcap_csv = pd.read_csv(args.input)
    new_dfs = extract_repeat_instruments(redcap_csv)
    if args.error_dates:
        new_dfs = remove_problem_dates(new_dfs, args.error_dates)
    output_dfs(output_dir, new_dfs)


if __name__ == '__main__':
    main(parse_args())
