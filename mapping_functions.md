# Mapping functions

## Mapping template format

Each line in the mapping template represents one field in the schema.
For example, `date_of_diagnosis` is part of the `primary_diagnoses` schema within a `DONOR`:

`DONOR.INDEX.primary_diagnoses.INDEX.date_of_diagnosis,`

The `INDEX` after the field name indicates that there can be multiple instances. For example, this line indicates there can be one or more primary diagnoses per DONOR, each with one or more specimens:

`DONOR.INDEX.primary_diagnoses.INDEX.specimens.INDEX.tumour_grade,`

Entries that begin with `##` are informational.

## Defining mapping functions

For each field, decide:

1. What column name in my input file(s) goes with this field?
2. Does the data need to be transformed to align with the expectations of the schema?
    a. If so, can I use a generic mapping function, or do I need to write my own?

The template suggests a default mapping, of the format `{mapping_function(DATA_SHEET.column_name)}`. If your data does not align with this, you may have to change this.

### Aligning field names

Sometimes your raw data contains column headings that do not exactly match the schema fields. For example, if your input file uses "Birthdate" instead of "date_of_birth", you may need to change the default mapping:

`DONOR.INDEX.date_of_birth, {single_val(DONOR_SHEET.Birthdate)}`

### Specifying index fields

For cases where there can be multiple instances of a schema (e.g. multiple treatments, or specimens), you _must_ specify an indexing field for that schema. In the template, this looks like a line ending in `INDEX` with the `indexed_on` mapping function:

```
DONOR.INDEX.primary_diagnoses.INDEX, {indexed_on(PRIMARY_DIAGNOSES_SHEET.submitter_donor_id)}
DONOR.INDEX.primary_diagnoses.INDEX.submitter_primary_diagnosis_id, {single_val(PRIMARY_DIAGNOSES_SHEET.submitter_primary_diagnosis_id)}
DONOR.INDEX.primary_diagnoses.INDEX.date_of_diagnosis, {single_date(PRIMARY_DIAGNOSES_SHEET.date_of_diagnosis)}
```

Here, `primary_diagnoses` will be added as an an array for the Donor with `submitter_donor_id`. Each entry in `primary_diagnoses` will use the values on the `PRIMARY_DIAGNOSES_SHEET` that have the same `submitter_donor_id`.

If your schema doesn't contain any instances of a particular indexed field, you can specify `NONE`:
`{indexed_on(NONE)}`

If your schema requires more complex mapping calculations, you can define an index function in your mapping file: it should return an array of index values.


## Transforming data using standard functions

In addition to mapping column names, you can also transform the values inside the cells to make them align with the schema. We've already seen the simplest case - the `single_val` function takes a single value for the named field and returns it (and should only be used when you expect one single value).

The standard functions are defined in `mappings.py`. They include functions for handling single values, list values, dates, and booleans.


## Writing your own custom functions

If the data cannot be transformed with one of the standard functions, you can define your own. In your data directory (the one that contains `manifest.yml`) create a python file (let's assume you called it `new_cohort.py`) and add the name of that file as the `mapping` entry in the manifest.

Following the format in the generic `mappings.py`, write your own functions in your python file for how to translate the data. To specify a custom mapping function in the template:

`DONOR.INDEX.primary_diagnoses.INDEX.basis_of_diagnosis,{new_cohort.custom_function(DATA_SHEET.field_name)}`

Examples:

To map input values to output values (in case your data capture used different values than the model):

```
def sex(data_value):
    # make sure we only have one value
    mapping_val = mappings.single_val(data_value)

    sex_dict = {
        'Female': 'F',
        'Male': 'M',
    }

    result = None
    for item in sex_dict:
        if (item == data_value) and (mappings.is_null(data_value)) is False:
            result = sex_dict[item]

    return result
```

You can explicitly create a dictionary based on multiple raw data values and have the mapping method's return value overwrite the rest of the entries in the dictionary:

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
