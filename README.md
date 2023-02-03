# clinical_ETL_code

This repository converts MoH clinical data into the packet format needed for katsu. The cohort-specific mappings are implemented in a private GitHub repository, not here. 

## Set-up & Installation
Prerequisites: 
- [Python 3.6+](https://www.python.org/)
- [pip](https://github.com/pypa/pip/)

You'll need to set up a free [account](https://bioportal.bioontology.org/account) at NCBI Bioportal to obtain an API key.

## Converting csvs to ingest packets

Most of the heavy lifting is done in the CSVConvert.py script. This script:
* takes an input directory of xlsx files and converts them to csv
* for each field for each patient, applies the appropriate mapping function to transform the raw data into valid model data
* exports the data into a json file(s) appropriate for ingest

```
$ python CSVConvert.py [-h] [--input INPUT] [--mapping|manifest MAPPING]

--input: path to dataset to be converted to data model

--manifest: Path to a manifest file describing the mapping
```

The output packets (`INPUT_map.json` and `INPUT_indexed.json`) will be in the parent of the `INPUT` directory. 

## Generating model template file

The `generate_template.py` script will generate a template file based an openapi.yaml file. 

```
$ python generate_schema.py -h
usage: generate_schema.py [-h] --url URL [--out OUT]

options:
  -h, --help  show this help message and exit
  --url URL   URL to openAPI schema file (raw github link)
  --out OUT   name of output file; csv extension will be added. Default is template

```

For using katsu with the MoHCCN data model, the URL to the schema is https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/docs/schema.yml (note raw github url).

## Testing
Continuous Integration is implemented through Pytest and Travis CI which runs when git pushes occur. Build results can be found at [this repository's Travis build page](https://travis-ci.com/github/CanDIG/medidata_mCode_ETL)

To run tests manually, enter from command line `$ pytest`

*Note: updated mCodePacket.json files must be pushed for all tests to pass during Travis builds*

## Creating a dummy json file for testing
You can use an mocode template file (created as described above) alone to create a dummy ingest file without actual data. 

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
* how much of the dataset is covered by the mapping