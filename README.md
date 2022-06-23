# medidata_mCode_ETL 
[![Build Status](https://travis-ci.com/CanDIG/medidata_mCode_ETL.svg?token=G1SY8JVFAzjkR7ZoffDu&branch=main)](https://travis-ci.com/CanDIG/medidata_mCode_ETL)

Convert medidata rave data to mCode model for Katsu ingestion with Python

## Creating a mapping
You'll need to create a mapping scheme for converting your raw data into mCodepackets for use by katsu. 
To generate a template for the current installed version of katsu, run:

`$ python CSVConvert.py --template output_file`

to create a csv file that you can fill in to create mappings.

Save this completed CSV file in a new directory. 

In this directory, place a manifest.yml file with the following information:

```yaml
description: Test mapping of COMPARISON dataset to mCODEpacket format for katsu
mapping: your_mapping.csv
mapping_functions:
  - additional_functions.py
```

Files should be specified as paths relative to the location of the manifest file.

You can specify nodes to be mapped using mapping functions, passing in the set of fields from your raw dataset that you want to map:

```python
subject.extra_properties, {additional_functions.vital_signs_node(WEIGHT_BEFORE_STD, WEIGHT_BEFORE_STD_UN, WEIGHT_25_AGE_STD, WEIGHT_25_AGE_STD_UN , HEIGHT_STD, HEIGHT_STD_UN)}
```

These are functions that accept a single argument, `mapping`, and return a python object:

```python
def vital_signs_node(mapping):
    vital_signs = {
        'WEIGHT_BEFORE_STD': 'weight_before_illness',
        'WEIGHT_BEFORE_STD_UN': 'weight_before_illness_unit',
        'WEIGHT_25_AGE_STD': 'weight_around_25',
        'WEIGHT_25_AGE_STD_UN': 'weight_around_25_unit',
        'HEIGHT_STD': 'height',
        'HEIGHT_STD_UN': 'height_unit'
    }
    new_dict = {}
    for item in mapping.keys():
        new_dict[vital_signs[item]] = mapping[item]
    return new_dict
```

Note that you can specify the particular field from a particular raw input sheet/csv:
```python
Patient.provinceOfResidence, {COMPARISON.province_from_site(Demographics.Site)}
```

Note that your manifest can specify additional mapping functions. These are contained in a python file in your manifest's directory.
Similarly, these python files should be specified relative to the path of the manifest file.

### Built-in mapping functions

Some transformations are pretty standard, so are provided in mappings.py. These don't require a module to be specified:
```
subject.date_of_birth,{date(BIRTH_DATE_YM_RAW)}
```

### Notes about how to specify mappings:

The entries available in the template represent the data mappable by katsu's mCODEpacket.

Data that should be a single value should use the built-in mapping function `single_val`; likewise any that should be a list/array should use `list_val`.

Any additional data that you'd like to include needs to be mapped to one of the extra_properties dicts.

Any mappings left blank will be stored as None in the resulting mCODEpacket.

Entries that begin with `##` are informational: they can be overwritten or deleted completely from the mapping file.

Entries that have an asterisk are required values for mCODEpacket.

Entries that contain a 0 in the name represent array values: probably the best way to 
specify mappings for these is to pass in all relevant data into a custom mapping function and create the array that way.
If you choose to do this, don't also specify mappings for sub-entries in the mapping file, as all of the mapping will
happen in the mapping function.

## Set-up & Installation
Prerequisites: 
- [Python 3.6+](https://www.python.org/)
- [pip](https://github.com/pypa/pip/)

You'll need to set up a free [account](https://bioportal.bioontology.org/account) at NCBI Bioportal to obtain an API key.

## Running from command line
`$ python CSVConvert.py [-h] [--input INPUT] [--template TEMPLATE] [--mapping|manifest MAPPING]`

--input: path to dataset to be converted to mcode data model

--template: If provided, generate a mapping template at the specified file

--mapping or --manifest: Path to a manifest file describing the mapping


## Testing
Continuous Integration is implemented through Pytest and Travis CI which runs when git pushes occur. Build results can be found at [this repository's Travis build page](https://travis-ci.com/github/CanDIG/medidata_mCode_ETL)

To run tests manually, enter from command line `$ pytest`

*Note: updated mCodePacket.json files must be pushed for all tests to pass during Travis builds*
