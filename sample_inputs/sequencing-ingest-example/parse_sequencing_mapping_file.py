import copy
import os
import argparse
import pandas as pd
import re
import glob
from pathlib import Path
import json


VERBOSE = False


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapping-csv', type=str, required=True, help="path to csv with mapping between clinical samples and genomic file locations")
    parser.add_argument('--verbose', '-v', action="store_true", help="Print extra information")
    parser.add_argument('--output', type=str, default="tmp_out",
                        help="Optional name of output directory; default is tmp_out in same input directory. "
                             "If --output doesn't exist, the directory will be created. Will overwrite anything in the "
                             "specified output directory of the same names.")
    args = parser.parse_args()
    return args


def create_csvs(mapping_df):
    normals_df = (copy.deepcopy(mapping_df).drop(['TUMOUR_SAMPLE_ID', 'VCF_TUMOUR_ID'], axis=1).
                  rename(columns={'NORMAL_SAMPLE_ID': 'sample_submitter_id',
                                  'VCF_NORMAL_ID': 'genomic_file_sample_id'}))
    tumour_df = (copy.deepcopy(mapping_df).drop(['NORMAL_SAMPLE_ID', 'VCF_NORMAL_ID'], axis=1).
                 rename(columns={'TUMOUR_SAMPLE_ID': 'sample_submitter_id',
                                 'VCF_TUMOUR_ID': 'genomic_file_sample_id'}))
    experiments_df = pd.concat([normals_df, tumour_df]).sort_values(by=['PATIENT_ID'])
    experiments_df['experiment_id'] = experiments_df['sample_submitter_id'] + "-EXP"
    experiments_df['library_description'] = "DNA sequencing library"
    experiments_df['instrument'] = "Illumina HiSeq 4000"
    experiments_df['library_selection'] = "size fractionation"
    experiments_df['protocol'] = "https://dx.doi.org/10.17504/protocols.io.bjdxki7n"
    experiments_df['library_source'] = "genomic"
    experiments_df['library_strategy'] = "WGS"
    experiments_df['library_layout'] = "paired"

    analyses_df = pd.concat([normals_df, tumour_df]).sort_values(by=['PATIENT_ID'])
    analyses_df['analysis_id'] = analyses_df['ECS_Path'].apply(lambda x: Path(Path(x).stem).stem)


    samples_df = pd.concat([normals_df, tumour_df]).sort_values(by=['PATIENT_ID'])
    samples_df['genomic_file_id'] = samples_df['ECS_Path'].apply(lambda x: Path(Path(x).stem).stem)

    main_df = copy.deepcopy(mapping_df)
    main_df['main_name'] = main_df['ECS_Path'].apply(lambda x: os.path.basename(x))
    main_df['reference'] = "hg38"
    main_df['sequence_type'] = "wgs"
    main_df['data_type'] = "variant"
    main_df['genomic_file_id'] = main_df['ECS_Path'].apply(lambda x: Path(Path(x).stem).stem)
    # add index columns
    index_df = copy.deepcopy(main_df[['PROGRAM_ID', 'ECS_Path', 'main_name']])
    index_df['index_path'] = index_df['ECS_Path'] + ".tbi"
    index_df['index_name'] = index_df['main_name'] + ".tbi"
    index_df['genomic_file_id'] = index_df['ECS_Path'].apply(lambda x: Path(Path(x).stem).stem)
    samples_df = copy.deepcopy(samples_df[['genomic_file_id', 'PATIENT_ID', 'sample_submitter_id',
                                           'genomic_file_sample_id']])
    return {
        "main": main_df,
        "index": index_df,
        "samples": samples_df
    }


def main(args):
    output_dir = args.output
    if os.path.isfile(output_dir):
        print("output file instead of directory given for --output, please specify your desired directory for output "
              "files.")
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    VERBOSE = args.verbose
    map_csv = pd.read_csv(args.mapping_csv)
    step_dfs = create_csvs(map_csv)


    for name, df in step_dfs.items():
        df.to_csv(os.path.normpath(f"{output_dir}/{name}.csv"), index=False)


if __name__ == '__main__':
    main(parse_args())
