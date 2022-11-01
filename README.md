# clinical_ETL_code

This repository converts MoH clinical data into the mcodepacket format needed for katsu. The cohort-specific mappings are implemented in a private GitHub repository, not here. 

## Set-up & Installation
Prerequisites: 
- [Python 3.6+](https://www.python.org/)
- [pip](https://github.com/pypa/pip/)

You'll need to set up a free [account](https://bioportal.bioontology.org/account) at NCBI Bioportal to obtain an API key.

## Running from command line
```
$ python CSVConvert.py [-h] [--input INPUT] [--template TEMPLATE] [--mapping|manifest MAPPING]

--input: path to dataset to be converted to mCODE data model

--template: If provided, generate a mapping template at the specified file (only needed if you are creating a new template sheet)

--mapping or --manifest: Path to a manifest file describing the mapping
```
## Testing
Continuous Integration is implemented through Pytest and Travis CI which runs when git pushes occur. Build results can be found at [this repository's Travis build page](https://travis-ci.com/github/CanDIG/medidata_mCode_ETL)

To run tests manually, enter from command line `$ pytest`

*Note: updated mCodePacket.json files must be pushed for all tests to pass during Travis builds*

## Creating a dummy json file for testing
You can use a template file (created as described above with `--template`) alone to create a dummy ingest file without actual data. 

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