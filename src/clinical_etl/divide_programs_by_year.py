# Divide a *_map.json by cohort year, appending either -Y12 or -Y45 to the program_id.
#
# Usage: refer to `python divide_programs_by_year.py --help`.
#
# Inputs:
# A *_map.json file, as produced by CSVConvert.py
# A .csv export of the Cases tab of the MoH-Q_Dashboard Google Sheet weekly report. Found in Google Drive -> C3G_MTL -> MoH_project -> MoH-Q_Dashboard

import argparse
import pathlib
import csv
import json
import sys
import re

def parse_args():
    parser = argparse.ArgumentParser(description="Divide a *_map.json by cohort year, appending either -Y12 or -Y45 to the program_id.")

    parser.add_argument("-i", "--input_json", type=str, help="MOH JSON in which to divide programs by year.", required=True, )
    parser.add_argument("-d", "--donor_years", type=str, help=".csv including donors and their year", required=True)

    args = parser.parse_args()

    # Validate the file paths.
    if not pathlib.Path(args.input_json).is_file():
        parser.error("The input_json file does not exist")
    if not re.search("_map.json", args.input_json):
        parser.error("The input_json file name must end with _map.json") 
    if not pathlib.Path(args.donor_years).is_file():
        parser.error("The donor_years file does not exist.")

    # Output the new, year-divided JSON to the same directory as the input JSON. 
    args.out_file = re.sub("_map.json", "_map_divided_by_year.json", args.input_json)
    return args

def parse_cases(donor_years):
    """Transform cases.csv into a lookup dict, mapping donors to only the values Y12 or Y45.
    Args:
        donor_years (string): The absolute path and filename of cases.csv.
    Returns:
        dict: {donor: [Y12 or Y45]}
    """
    donor_year_lookup = dict()
    with open(donor_years, mode="r") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            donor_year_lookup[row["Case"]] = row["ProjectYear"]
    # Minor validation of year values
    unique_years = set(donor_year_lookup.values())
    if not unique_years == {"Y1", "Y2", "Y4", "Y5"}:
        sys.exit(f"Invalid years present in: {unique_years}")
    # Combine Y1, Y2 into Y12; and Y4, Y5 into Y45.
    for donor, year in donor_year_lookup.items():
        if year in ["Y1", "Y2"]:
            donor_year_lookup[donor] = "Y12"
        if year in ["Y4", "Y5"]:
            donor_year_lookup[donor] = "Y45"
    return donor_year_lookup

def update_json(args, donor_year_lookup):
    """
    Generate a new JSON, with cohorts divided into Y12 and Y45.
    Args:
        args (Object): The parsed CLI args.
        donor_year_lookup (dict): Year lookup for each donor.  Format: {donor: [Y12 or Y45]}
    """
    try:
        with open(args.input_json, 'r') as input_json_file:
            data = json.load(input_json_file)
            for donor in data["donors"]:
                if donor["submitter_donor_id"] in donor_year_lookup.keys():
                    # Append -Y12 or -Y45 to the program_id.
                    donor["program_id"] = donor["program_id"] + "-" + donor_year_lookup[donor["submitter_donor_id"]]
                else:
                    sys.exit(f"Donor '{donor["submitter_donor_id"]}' not found in year lookup.")
    except FileNotFoundError:
        print(f"Error: The file '{args.input_json}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from the file '{args.input_json}'. Check if the JSON is valid.")
    # Write the output file.
    with open(args.out_file, 'w') as f:
        f.write(json.dumps(data, indent=4))

def main():
    args = parse_args()
    # print(args) # For testing...
    donor_year_lookup = parse_cases(args.donor_years)
    update_json(args, donor_year_lookup)

if __name__ == "__main__":
    main()
