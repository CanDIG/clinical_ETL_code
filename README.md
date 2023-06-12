# clinical_ETL_code

This repository converts MoH clinical data into the packet format needed for katsu.

## Set-up & Installation
Prerequisites:
- [Python 3.6+](https://www.python.org/)
- [pip](https://github.com/pypa/pip/)

## Creating a mapping
You'll need to create a mapping scheme for converting your raw data into the json packets for use by katsu. Mappings for existing CanDIG cohorts and ingesters are located in a [private repository](https://github.com/CanDIG/clinical_ETL_data); the following instructions will help you create a new mapping.

#### 1. Generate a schema for the desired version of katsu:
The `generate_template.py` script will generate a template file based an openapi.yaml file.

```
$ python generate_schema.py -h
usage: generate_schema.py [-h] --url URL [--out OUT]

options:
  -h, --help  show this help message and exit
  --url URL   URL to openAPI schema file (raw github link)
  --out OUT   name of output file; csv extension will be added. Default is template

```

For using katsu with the current MoHCCN data model, the URL to the schema is https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/docs/schema.yml (note raw github url).


#### 2. Fill in the fields in the template files by naming your mapping functions and their input.
Example:

`id, {single_val(Subject)}`

In this case,  the `id` field in the MoH packet is being mapped to the `Subject` column of the raw input data using the built-in `single_val` function.

You can specify nodes to be mapped using custom mapping functions, passing in the set of fields from your raw dataset that you want to map:

`subject.extra_properties, {additional_functions.vital_signs_node(WEIGHT_BEFORE_STD, WEIGHT_BEFORE_STD_UN, WEIGHT_25_AGE_STD, WEIGHT_25_AGE_STD_UN , HEIGHT_STD, HEIGHT_STD_UN)}`

In this case, the `extra_properties` field in  the MoH packet is being mapped to multiple columns of the raw input data, and the custom mapping function is called `vital_signs_node` from the `additional_functions` module.

Note that you can specify the particular field from a particular raw input sheet/csv:
`Patient.provinceOfResidence, {COMPARISON.province_from_site(Demographics.Site)}`

**Notes about mapping functions:**

- The entries available in the template represent the data mappable by katsu's MoHpacket. Each entry can specify a mapping function to correlate an entry in the raw data to the entry in the MoHpacket.

- Entries that begin with `##` are informational: they can be overwritten or deleted completely from the mapping file.

- Entries that contain additional `.entry` parts represent nesting properties in a dictionary:

```
##prop_a,
##prop_a.prop_b,
prop_a.prop_b.prop_c, {single_val(dataval_c)}
prop_a.prop_b.prop_d, {single_val(dataval_d)}

represents the following JSON dict:
{
  "prop_a": {
      "prop_b":
        {
          "prop_c": dataval_c,
          "prop_d": dataval_d
        }
    }
}
```

Note that in this example, the entries for `prop_a` and `prop_b` are listed as informational: if `prop_c` and `prop_d` are explicitly mapped, `prop_a` and `prop_b` don't need to be.

<details>
<summary>What if I have a complex mapping?</summary>

You can explicitly create a dictionary based on multiple raw data values and have the mapping method's return value overwrite the rest of the entries in the dictionary. Using the same example as above:
```
##prop_a,
prop_a.prop_b, {my_mapping_func(dataval_c, dataval_d)}

with

def my_mapping_func(data_values) {
  return {
    "prop_c": "FOO_" + mappings.single_val(data_values['dataval_c']),
    "prop_d": "BAR_" + mappings.single_val(data_values['dataval_d']),
  }
}

represents the following JSON dict:
{
  "prop_a": {
      "prop_b":
        {
          "prop_c": "FOO_dataval_c",
          "prop_d": "BAR_dataval_d"
        }
    }
}

```
</details>

- Entries that end with a 0 in the name represent arrays: if there are subsequent entries after the first line ending with 0, this represents an array of dicts. The first entry ending in 0 can be mapped to an index field using the `{indexed_on(FIELD)}` notation. Any subsequent subentries in the dict will be mapped into the corresponding dict in the array.

```
prop_a.0
prop_a.0.prop_b
prop_a.0.prop_c

represents the following JSON:

{
  "prop_a": [
    {
      "prop_b": mapping,
      "prop_c": mapping
    }
  ]
}
```

- Data that should be a single value should use the built-in mapping function `single_val`; likewise any that should be a list/array should use `list_val`. **Note**: single value means a patient will only have one value for that field, such as `id` or `sex`. Something like `genetic_variant` would not be single value, since a single patient can have more than one.

- Some transformations are pretty standard, so are provided in `mappings.py`. These don't require a module to be specified:
`subject.date_of_birth,{single_date(BIRTH_DATE_YM_RAW)}`

- For template entries that do not have an explicit mapping specified, CSVConvert will try to find a value in the raw data with the same name. If none is found, CSVConvert will skip that entry.

<!-- - Entries that have an asterisk are required values for MoHpacket. There is no validation for this at the moment so the tool will run even if there are missing required values.
 -->
- Some editors (such as LibreOffice) insert commas in the template's empty fields and modify some names with hashtags. If the tool is not working, make sure to remove these characters using a text editor. Refer to this [example](https://github.com/CanDIG/clinical_ETL/blob/main/example/COMPARISON2mCODE.csv).



#### 3. Write your custom mapping functions.

Implement the custom mapping functions that you specified in your template file. These are functions that accept a single object, `data_values`, as an argument, and return a python object:

```python
# Example mapping function
def vital_signs_node(data_values):
    vital_signs = {
        'WEIGHT_BEFORE_STD': 'weight_before_illness',
        'WEIGHT_BEFORE_STD_UN': 'weight_before_illness_unit',
        'WEIGHT_25_AGE_STD': 'weight_around_25',
        'WEIGHT_25_AGE_STD_UN': 'weight_around_25_unit',
        'HEIGHT_STD': 'height',
        'HEIGHT_STD_UN': 'height_unit'
    }
    new_dict = {}
    for item in data_values.keys():
        new_dict[vital_signs[item]] = data_values[item]
    return new_dict
```

#### 4. Create a new directory that contains your template and mapping functions, then create a `manifest.yml` file in the same directory with the following information:
- `description`: description of the mapping
- `identifier`: column used to identify patients in the input data
- `mapping`: template file
- `functions`: additional mapping functions
- `sheets`: lists of sheets in the clinical data:
    - raw (all sheets available for mapping)
    - final (subset of sheets actually used in the mapping)
- `indexed`: a list of sheets that need a numeric row index, e.g. for specifying particular rows. Any sheets here will have an `index` column available to mapping functions.

**Note:** Files should be specified as paths relative to the location of the manifest file.

Example:
```yaml
description: Test mapping of COMPARISON dataset to MoHpacket format for katsu
identifier: Subject
mapping: your_mapping.csv
functions:
  - additional_functions.py
sheets:
  raw:
      - Vital Signs
      - Diagnosis
      - Diagnosis 2
      - Hematology
      - Outcome
  final:
      - Vital Signs
      - Diagnosis
      - Outcome
indexed:
      - Diagnosis
```

## Running from command line
`$ python clinical_ETL_code/CSVConvert.py [-h] [--input INPUT] [--template TEMPLATE] [--mapping|manifest MAPPING]`

--input: path to dataset to be converted to MoH data model

--template: If provided, generate a mapping template at the specified file (only needed if you are creating a new template sheet)

--mapping or --manifest: Path to a manifest file describing the mapping


## Converting csvs to ingest packets

Most of the heavy lifting is done in the CSVConvert.py script. This script:
* reads an input directory of xlsx or csv files (if xlsx, converts them to csv)
* reads a template file that contains a list of fields and (if needed) a mapping function
* for each field for each patient, applies the mapping function to transform the raw data into valid model data
* exports the data into a json file(s) appropriate for ingest

```
$ python CSVConvert.py [-h] [--input INPUT] [--manifest manifest_file]

--input: path to dataset to be converted to data model

--manifest: Path to a manifest file with settings for the ETL
```

The output packets (`INPUT_map.json` and `INPUT_indexed.json`) will be in the parent of the `INPUT` directory.


## Testing
Continuous Integration is implemented through Pytest and GitHub Actions which run when pushes occur. Build results can be found at [this repository's GitHub Actions page](https://github.com/CanDIG/clinical_ETL_code/actions/workflows/test.yml).

To run tests manually, enter from command line `$ pytest`


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