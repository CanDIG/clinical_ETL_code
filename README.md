# clinical_ETL_code

Convert patient clinical data to mCode model for Katsu ingestion with Python

## Creating a mapping   
You'll need to create a mapping scheme for converting your raw data into mCodepackets for use by katsu.

#### 1. Generate a template for the current installed version of katsu:

`$ python CSVConvert.py --template output_file`

#### 2. Fill in the fields in the template files by naming your mapping functions and their input. 
Example: 

`id, {single_val(Subject)}`

In this case,  the `id` field in  the mCODE packet is being mapped to the `Subject` column of the raw input data using the built-in `single_val` function.

You can specify nodes to be mapped using custom mapping functions, passing in the set of fields from your raw dataset that you want to map:

`subject.extra_properties, {additional_functions.vital_signs_node(WEIGHT_BEFORE_STD, WEIGHT_BEFORE_STD_UN, WEIGHT_25_AGE_STD, WEIGHT_25_AGE_STD_UN , HEIGHT_STD, HEIGHT_STD_UN)}`

In this case,  the `extra_properties` field in  the mCODE packet is being mapped to multiple columns of the raw input data, and the custom mapping function is called `vital_signs_node` from the `additional_functions` module.

Note that you can specify the particular field from a particular raw input sheet/csv:
`Patient.provinceOfResidence, {COMPARISON.province_from_site(Demographics.Site)}`

**Notes about mapping functions:**

- The entries available in the template represent the data mappable by katsu's mCODEpacket.

- Data that should be a single value should use the built-in mapping function `single_val`; likewise any that should be a list/array should use `list_val`. **Note**: single value means a patient will only have one value for that field, such as `id` or `sex`. Something like `genetic_variant` would not be single value, since a single patient can have more than one.

- Some transformations are pretty standard, so are provided in `mappings.py`. These don't require a module to be specified:
`subject.date_of_birth,{date(BIRTH_DATE_YM_RAW)}`

- Any additional data that you'd like to include and is not part of the mCODE fields needs to be mapped to one of the extra_properties dicts.

- Any mappings left blank will be stored as None in the resulting mCODEpacket.

- Entries that begin with `##` are informational: they can be overwritten or deleted completely from the mapping file.

- Entries that have an asterisk are required values for mCODEpacket. There is no validation for this at the moment so the tool will run even if there are missing required values.

- Entries that contain a 0 in the name represent array values: probably the best way to 
specify mappings for these is to pass in all relevant data into a custom mapping function and create the array that way. If you choose to do this, don't also specify mappings for sub-entries in the mapping file, as all of the mapping will
happen in the mapping function.

- Some editors (such as LibreOffice) insert commas in the template's empty fields and modify some names with hastags. If the tool is not working, make sure to remove these characters using a text editor. Refer to this [example](https://github.com/CanDIG/clinical_ETL/blob/main/example/COMPARISON2mCODE.csv).

#### 3. Write your custom mapping functions.

Implement the custom mapping functions that you specified in you template file. These are functions that accept a single argument, `mapping`, and return a python object:

```python
# Example mapping function
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
description: Test mapping of COMPARISON dataset to mCODEpacket format for katsu
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

`python create_test_mapping.py` creates a file at `mcode_template_testmap.json` that is filled in (without using mapping functions) with placeholder or dummy values. You can specify the placeholder value with the argument `--placeholder`.

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