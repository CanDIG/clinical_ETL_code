# clinical_ETL_code

This repository converts input csv files with clinical (phenotypic) data into a json aligned with a provided openapi schema. You can provide custom mapping functions to transform data in your input file before writing to the json.

Specifically, this code was designed to convert clinical data for the MOHCCN project into the packet format needed for ingest into CanDIG's clinical data service (katsu).

## Set-up & Installation
Prerequisites:
- [Python 3.6+](https://www.python.org/)
- [pip](https://github.com/pypa/pip/)


## Running from the command line

Most of the heavy lifting is done in the CSVConvert.py script. See sections below for setting up the inputs. This script:
* reads an file (.xlsx or .csv) or a directory of files (csv)
* reads a template file that contains a list of fields and (if needed) a mapping function
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

## Input file format

The input for CSVConvert is either a single xlsx file, a single csv, or a directory of csvs. If providing a spreadsheet, there can be multiple sheets (usually one for each sub-schema).

All rows must contain identifiers that allow linkage to the containing schema, for example, a row that describes a Treatment must have a link to the Donor / Patient id for that Treatment.

Data should be (tidy)[https://r4ds.had.co.nz/tidy-data.html], with each variable in a separate column, each row representing an observation, and a single data entry in each cell.

Depending on the format of your raw data, you may need to write an additional tidying script to pre-process. For example, the `ingest_redcap_data.py` converts the export format from redcap into a set of input csvs for CSVConvert.

## Setting up a cohort directory

For each dataset (cohort) that you want to convert, create a directory outside of this repository. For CanDIG devs, this will be in the private `data` repository. This cohort directory should contain:

* a `manifest.yml` file with settings for the mapping
* the template file lists custom mappings for each field
* (if needed) a python file that implements any cohort-specific mapping functions

**Important:** If you are placing this directory under version control and the cohort is not sample / synthetic data, do not place raw or processed data files in this directory, to avoid any possibility of committing protected data.

## Manifest file
The `manifest.yml` file contains settings for the cohort mapping. There is a sample file in `sample_inputs/manifest.yml` with documentation. The fields are:

```
description: A brief description
mapping: the csv file that lists the mappings for each field
identifier: submitter_donor_id
schema: a URL to the openapi schema file
functions:
  - cohort-mapping-functions
```
## Mapping template

You'll need to create a mapping template that defines which mapping functions (if any) should be used for which fields.

The `generate_template.py` script will generate a template file based an openapi.yaml file. For using katsu with the current MoHCCN data model, the URL to the schema is https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/docs/schema.yml (note raw github url).

```
$ python generate_schema.py -h
usage: generate_schema.py [-h] --url URL [--out OUT]

options:
  -h, --help  show this help message and exit
  --url URL   URL to openAPI schema file (raw github link)
  --out OUT   name of output file; csv extension will be added. Default is template

```
Each line in the mapping template will have a suggested mapping function to map a field on an input sheet to a field in the schema. Replace the generic sheet names with your sheet names. You may need to replace suggested field names with your own field names, if they differ.

If your data do not map in the same way as the suggested mapping functions, you may need to write your own mapping functions. See the [mapping instructions](mapping_functions.md) for detailed documentation on writing your own mapping functions.

**Note**: Do not edit, delete, or re-order the template lines, except to add mapping functions after the comma in each line.

## Testing

Continuous integration testing for this repository is implemented through Pytest and GitHub Actions which run when pushes occur. Build results can be found at [this repository's GitHub Actions page](https://github.com/CanDIG/clinical_ETL_code/actions/workflows/test.yml).

To run tests manually, enter from command line `$ pytest`

## Validating the mapping

You can validate the generated json mapping file against the MoH data model. The validation will compare the mapping to the json schema used to generate the template, as well as other known requirements and data conditions specified in the MoH data model.
```
$ python validate_coverage.py [-h] [--input map.json] [--manifest MAPPING]

--json: path to the map.json file created by CSVConvert

--manifest: Path to a manifest file describing the mapping
```
Issues caused by failed requirements will throw exceptions: these must be addressed before validation can be completed. Issues caused by failed conditions in the MoH model will be listed in the output.


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