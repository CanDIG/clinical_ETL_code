""" 
Methods to transform the redcap raw data into the csv format expected by 
CSVConcert.py
"""

import os
import argparse
import re
import pandas
import json
from pathlib import Path 

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required = True, help="Path to either an xlsx file or a directory of csv files for ingest")
    parser.add_argument('--verbose', '--v', action="store_true", help="Print extra information")
    parser.add_argument('--output', type=str, default="tmp_out", help="Optional name of output directory in parent of input path; default tmp_out")
    args = parser.parse_args()
    return args

def ingest_redcap_files(input_path):
    """Test of ingest of redcap output files"""
    raw_csv_dfs = {}
    if os.path.isdir(input_path):
        files = os.listdir(input_path)
        for file in files:
            file_match = re.match(r"(.+)\.csv$", file)
            if file_match is not None:
                print(f"Reading input file {file}")
                df = pandas.read_csv(os.path.join(input_path, file), dtype=str, encoding = "latin-1")
                #print(f"initial df shape: {df.shape}")
                # find and drop empty columns
                df = drop_empty_columns(df)
                # now we do some renaming, becuase for reasons we don't understand
                # the program_id and submitter_donor_id columns are swapped
                df.rename(columns={'program_id':'tempname'},inplace=True)
                df.rename(columns={'submitter_donor_id':'program_id'},inplace=True)
                df.rename(columns={'tempname':'submitter_donor_id'},inplace=True)
                raw_csv_dfs[file_match.group(1)] = df 
    else:
        print("Error: expecting directory of input files for --input option")
    return raw_csv_dfs

def extract_repeat_instruments(df):
    """ Transforms the single (very sparse) dataframe into one dataframe per 
    MoH schema. This makes it easier to look at, and also eliminates a bunch
    of pandas warnings."""
    new_dfs={}
    starting_rows = df.shape[0]
    repeat_instruments = df['redcap_repeat_instrument'].dropna().unique()
    total_rows = 0
    for i in repeat_instruments:
        # each row has a redcap_repeat_instrument that describes the schema
        # (e.g. Treatmnet) and a redcap_repeat_instance that is an id for that 
        # schema (this would be the treatment.id)
        print(f"Extracting schema {i}")
        schema_df = df.loc[df['redcap_repeat_instrument'] == i]
        # drop all of the empty columns that aren't relevent for this schema
        schema_df = drop_empty_columns(schema_df)
        # rename the redcap_repeat_instance to the specific id (e.g. treatment_id)
        schema_df.rename(columns={
            'redcap_repeat_instance': f"{i}_id"
            },
            inplace=True
            )
        total_rows += schema_df.shape[0]
        new_dfs[i]=schema_df

    # now save all of the rows that aren't a repeat_instrument and 
    # label them Singleton for now
    singletons = df.loc[df['redcap_repeat_instrument'].isnull()]
    singletons = drop_empty_columns(singletons)
    # check that we have all of the rows
    if (total_rows + singletons.shape[0] < starting_rows):
        print("Warning: not all rows recovered in raw data")
    new_dfs['Singleton']=singletons
    return new_dfs

def drop_empty_columns(df):
    empty_cols = [col for col in df if df[col].isnull().all()]  
    df = df.drop(empty_cols, axis=1)
    return df

def output_dfs(input_path,output_dir,df_list):
    parent_path = Path(input_path).parent
    tmpdir = Path(parent_path,output_dir)
    if not tmpdir.is_dir():
        tmpdir.mkdir()
    print(f"Writing output files to {tmpdir}")
    for d in df_list:
        df_list[d].to_csv(Path(tmpdir,f"{d}.csv"), index=False)

def main(args):
    input_path = args.input

    raw_csv_dfs = ingest_redcap_files(input_path)
    new_dfs = extract_repeat_instruments(raw_csv_dfs['combined'])
    output_dir = args.output
    output_dfs(input_path,output_dir,new_dfs)

if __name__ == '__main__':
    main(parse_args())