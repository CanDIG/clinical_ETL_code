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
    args = parser.parse_args()
    return args

def ingest_redcap_files(input_path):
    """Test of ingest of redcap output files"""
    raw_csv_dfs = {}
    outputfile = "mohpacket"
    if os.path.isdir(input_path):
        output_file = os.path.normpath(input_path)
        files = os.listdir(input_path)
        for file in files:
            print(f"Reading input file {file}")
            file_match = re.match(r"(.+)\.csv$", file)
            if file_match is not None:
                df = pandas.read_csv(os.path.join(input_path, file), dtype=str, encoding = "latin-1")
                #print(f"initial df shape: {df.shape}")
                # find and drop empty columns
                empty_cols = [col for col in df if df[col].isnull().all()]  
                print(f"Dropped {len(empty_cols)} empty columns")
                df = df.drop(empty_cols, axis=1)
                print(f"final df shape: {df.shape}")
                raw_csv_dfs[file_match.group(1)] = df 
    return raw_csv_dfs

def extract_repeat_instruments(df):
    """ Transforms the single (very sparse) dataframe into one dataframe per 
    MoH schema."""
    new_dfs={}
    print(df.shape[0])
    repeat_instruments = df['redcap_repeat_instrument'].dropna().unique()
    print(repeat_instruments)
    total_rows = 0
    for i in repeat_instruments:
        # each row has a redcap_repeat_instrument that describes the schema
        # (e.g. Treatmnet) and a redcap_repeat_instance that is an id for that 
        # schema (this would be the treatment.id)
        print(f"Schema {i}")
        schema_df = df.loc[df['redcap_repeat_instrument'] == i]
        empty_cols = [col for col in schema_df if schema_df[col].isnull().all()]  
        schema_df = schema_df.drop(empty_cols, axis=1)
        schema_df.rename(columns={
            'redcap_repeat_instance':'id',
            'program_id':'submitter_donor_id'
            },
            inplace=True
            )
        total_rows += schema_df.shape[0]
        new_dfs[i]=schema_df
    print(total_rows)
    # now save all of the rows that aren't a repeat_instrument and 
    # label them Singleton for now
    df = df.loc[df['redcap_repeat_instrument'].isnull()]
    print(df.shape[0])
    new_dfs['Singleton']=df
    return new_dfs

def output_dfs(input_path,df_list):
    parent_path = Path(input_path).parent
    tmpdir = Path(parent_path,"tmp_out")
    if not tmpdir.is_dir():
        tmpdir.mkdir()
    for d in df_list:
        df_list[d].to_csv(Path(tmpdir,f"{d}.csv"))

def main(args):
    input_path = args.input
    #mappings.VERBOSE = args.verbose

    raw_csv_dfs = ingest_redcap_files(input_path)
    new_dfs = extract_repeat_instruments(raw_csv_dfs['combined'])
    for df in new_dfs:
        print(df)
        print(new_dfs[df])
    output_dfs(input_path,new_dfs)

    #repeat_instruments = raw_csv_dfs['combined']['redcap_repeat_instrument'].dropna()unique()
    #print(repeat_instruments)

if __name__ == '__main__':
    main(parse_args())