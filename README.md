# clinical_ETL_code

This repository converts input csv files with clinical (phenotypic) data into a json aligned with a provided openapi schema. You can provide custom mapping functions to transform data in your input file before writing to the json.

Specifically, this code was designed to convert clinical data for the MOHCCN project into the packet format needed for ingest into CanDIG's clinical data service (katsu).

## Set-up & Installation
Prerequisites:
- [Python 3.10+](https://www.python.org/)
- [pip](https://github.com/pypa/pip/)


## Running from the command line

Most of the heavy lifting is done in the [`CSVConvert.py`](CSVConvert.py) script. See sections below for setting up the inputs. This script:
* reads a file (.xlsx or .csv) or a directory of files (csv)
* reads a [template file](#mapping-template) that contains a list of fields and (if needed) a mapping function
* for each field for each patient, applies the mapping function to transform the raw data into valid model data
* exports the data into a json file(s) appropriate for ingest

```
$ python CSVConvert.py [-h] [--input INPUT] [--manifest manifest_file] [--test] [--verbose]

--input: path to dataset to be converted to data model

--manifest: Path to a manifest file with settings for the ETL

--verbose prints out extra statements for debugging where things have gone wrong

--test allows you to add extra lines to your manifest's template file that will be populated in the mapped schema. NOTE: this mapped schema will likely not be a valid mohpacket: it should be used only for debugging.
```

The output packets (`INPUT_map.json` and `INPUT_indexed.json`) will be in the parent of the `INPUT` directory / file.

Validation will automatically be run after the conversion is complete. Any validation errors or warnings will be reported both on the command line and as part of the `INPUT_map.json` file.

## Format of the output file

```
{
    "openapi_url": "https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/docs/schema.yml",
    "katsu_sha": < git sha of the katsu version used for the schema >,
    "donors": < An array of JSON objects, each one representing a DonorWithClinicalData in katsu >,
    "validation_warnings": [
        < any validation warnings, e.g. >
        "DONOR_5: cause_of_death required if is_deceased = Yes"
    ],
    "validation_errors": [
        < any validation errors, e.g. >
        "DONOR_5 > PD_5 > TR_5 > Radiation 1: Only one radiation is allowed per treatment"
    ],
    "statistics": {
        "required_but_missing": {
            < for each schema in the model, a list of required fields and how many cases are missing this value (out of the total number of occurrences) >
            "donors": {
              "submitter_donor_id": {
                  "total": 6,
                  "missing": 0
              }
        },
        "schemas_used": [
            "donors"
        ],
        "cases_missing_data": [
            "DONOR_5"
        ],
        "schemas_not_used": [
            "exposures",
            "biomarkers"
        ],
        "summary_cases": {
            "complete_cases": 13,
            "total_cases": 14
        }
    }
}
```

## Input file format

The input for `CSVConvert` is either a single xlsx file, a single csv, or a directory of csvs. If providing a spreadsheet, there can be multiple sheets (usually one for each sub-schema).

All rows must contain identifiers that allow linkage to the containing schema, for example, a row that describes a Treatment must have a link to the Donor / Patient id for that Treatment.

Data should be (tidy)[https://r4ds.had.co.nz/tidy-data.html], with each variable in a separate column, each row representing an observation, and a single data entry in each cell. In the case of fields that can accept an array of values, the values within a cell should be delimited such that a mapping function can accurately return an array of permissible values.

Depending on the format of your raw data, you may need to write an additional tidying script to pre-process. For example, the `ingest_redcap_data.py` converts the export format from redcap into a set of input csvs for CSVConvert.

## Setting up a cohort directory

For each dataset (cohort) that you want to convert, create a directory outside of this repository. For CanDIG devs, this will be in the private `data` repository. This cohort directory should contain the same elements as shown in the `sample_inputs` directory, which are:

* a `manifest.yml` file with settings for the mapping
* the template csv that lists custom mappings for each field (based on `moh_template.csv`)
* (if needed) a python file that implements any cohort-specific mapping functions

> [!IMPORTANT]
> If you are placing this directory under version control and the cohort is not sample / synthetic data, do not place raw or processed data files in this directory, to avoid any possibility of committing protected data.

## Manifest file
The `manifest.yml` file contains settings for the cohort mapping. There is a sample file in `sample_inputs/manifest.yml` with documentation. The fields are:

| field       | description                                                                                                                                                           |
|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| description | A brief description of what mapping task this manifest is being used for                                                                                              |
| mapping     | the mapping template csv file that lists the mappings for each field based on `moh_template.csv`, assumed to be in the same directory as the `manifest.yml` file      |
| identifier  | the unique identifier for the donor or root node                                                                                                                      |
| schema      | a URL to the openapi schema file                                                                                                                                      |
| functions   | A list of one or more filenames containing additional mapping functions, can be omitted if not needed. Assumed to be in the same directory as the `manifest.yml` file |

## Mapping template

You'll need to create a mapping template that defines the mapping between the fields in your input files and the fields in the target schema. It also defines what mapping functions (if any) should be used  to transform the input data into the required format to pass validation under the target schema.

Each line in the mapping template is composed of comma separated values with two components. The first value is an `element` or field from the target schema and the second value contains a suggested `mapping method` or function to map a field from an input sheet to the identified `element`. Each `element`, shows the full object linking path to each field required by the model. These values should not be edited.

If you're generating a mapping for the current MoH model, you can use the pre-generated [`moh_template.csv`](moh_template.csv) file. This file is modified from the auto-generated template to update a few fields that require specific handling. 

You will need to edit the `mapping method` column in the following ways:
1. Replace the generic sheet names (e.g. `DONOR_SHEET`, `SAMPLE_REGISTRATIONS_SHEET`) with the sheet names you are using as your input to `CSVConvert.py`
2. Replace suggested field names with the relevant field/column names in your input sheets, if they differ

If the field does not map in the same way as the suggested mapping function you will also need to:
3. Choose a different existing [mapping function](mappings.py) or write a new function that does the required transformation. See the [mapping instructions](mapping_functions.md) for detailed documentation on writing your own mapping functions.

>[!NOTE] 
> * Do not edit, delete, or re-order the template lines, except to adjust the sheet name, mapping function and field name in the `mapping method` column.
> * Fields not requiring mapping can be commented out with a # at the start of the line

<details>
<summary>Generating a template from a different schema</summary>
The `generate_schema.py` script will generate a template file based an openapi.yaml file.

```
$ python generate_schema.py -h
usage: generate_schema.py [-h] --url URL [--out OUT]

options:
  -h, --help  show this help message and exit
  --url URL   URL to openAPI schema file (raw github link)
  --out OUT   name of output file; csv extension will be added. Default is template

```
</details>

## Testing

Continuous integration testing for this repository is implemented through Pytest and GitHub Actions which run when pushes occur. Build results can be found at [this repository's GitHub Actions page](https://github.com/CanDIG/clinical_ETL_code/actions/workflows/test.yml).

To run tests manually, enter from command line `$ pytest`

### When tests fail...

<details>
<summary>"Compare moh_template.csv" fails</summary>

### You changed the `moh_template.csv` file:

To fix this, you'll need to update the diffs file. Run `bash update_moh_template.sh` and commit the changes that are generated for `test_data/moh_diffs.txt`.

### You did not change the `moh_template.csv` file:

There have probably been MoH model changes in katsu.

Run the `update_moh_template.sh` script to see what's changed in `test_data/moh_diffs.txt`. Update `moh_template.csv` to reconcile any differences, then re-run `update_moh_template.sh`. Commit any changes in both `moh_template.csv` and `test_data/moh_diffs.txt`.
</details>

## Validating the mapping

You can validate the generated json mapping file against the MoH data model. The validation will compare the mapping to the json schema used to generate the template, as well as other known requirements and data conditions specified in the MoH data model.
```
$ python validate_coverage.py [-h] [--input map.json] [--manifest MAPPING]

--json: path to the map.json file created by CSVConvert

--manifest: Path to a manifest file describing the mapping
```
The output will report errors and warnings separately. Jsonschema validation failures and other data mismatches will be listed as errors, while fields that are conditionally required as part of the MoH model but are missing will be reported as warnings.


<!-- # NOTE: the following sections have not been updated for current versions.

## Creating a dummy json file for testing
You can use an mohcode template file (created as described above) alone to create a dummy ingest file without actual data.

`python create_test_mapping.py` creates a JSON that is filled in (without using mapping functions) with placeholder or dummy values. You can specify the placeholder value with the argument `--placeholder`. If no template file is specified with `--template`, the current MCODE_SCHEMA of katsu is used and the JSON is outputted to stdout. Otherwise, the file is saved to `<template>_testmap.json`.

This JSON file can be ingested into katsu and compared with the ingested value using https://github.com/CanDIG/candigv2-ingest/blob/main/katsu_validate_dataset.py.

## Quantifying coverage for datasets and mappings
The `quantify_coverage.py` tool takes the same arguments as `CSVConvert.py`:
```
$ python CSVConvert.py [-h] [--input INPUT] [--mapping|manifest MAPPING]

--input: path to dataset

--mapping or --manifest: Path to a manifest file describing the mapping
```

This tool outputs information quantifying:
* how much of the schema is covered by the mapping
* how much of the dataset is covered by the mapping -->
