# Mapping functions

## Mapping template format

Each line in the mapping template represents one field in the schema. This may be a top-level field, e.g. `cause_of_death` is associated with the top-level schema (generally Patient / Donor / Individual).

`cause_of_death,`

or a nested field - here, `date_of_diagnosis` is part of the `primary_diagnoses` schema:

`primary_diagnoses.INDEX.date_of_diagnosis,`

The `INDEX` after the field name indicates that there can be multiple instances, for example, this line indicates there can be one ore more primary diagnoses, each with one or more specimens:

`primary_diagnoses.INDEX.specimens.INDEX.tumour_grade,`

Entries that begin with `##` are informational.

## Defining mapping functions

For each field, decide:

1. What column name in my input file(s) goes with this field?
2. Does the data need to be transformed to align with the expectations of the schema?
    a. If so, can I use a generic mapping function, or do I need to write my own?

You define mappings by adding a `{function}` after the last comma in the line. Details below!

## Perfectly matching data

If your input data aligns perfectly with the schema (the column names are exact and unambiguous, and the field data matches the format specified by the schema), you do not need to add a mapping function for that field.

For example, if the schema defines a field called `gender` with permissible values `[Man, Woman, Non-binary]` and your input file contains a field called `gender` with only these values, you do not have to add a mapping function.


### Aligning field names

Sometimes your raw data contains column headings that do not exactly match the schema fields. For example, if you input file uses "Birthdate" instead of "date_of_birth", add the following:

`date_of_birth, {single_val(Birthdate)}`

If there is more than one field with the same name, you can specify the specific file / sheet using this notation (here, Birthdate is in the sheet / file called Donor):

`date_of_birth, {single_val(Donor.Birthdate)}`

### Specifying index fields

For cases where there can be multiple instances of a schema (e.g. multiple treatments, or specimens), you _must_ specify an indexing field for that schema. In the template, this looks like a line ending in `INDEX` followed by other fields nested underneath, e.g. for `primary_diagnoses`:

```
primary_diagnoses.INDEX,
primary_diagnoses.INDEX.submitter_primary_diagnosis_id,
primary_diagnoses.INDEX.date_of_diagnosis,
```

You need to specify the indexing field for primary diagnosis. This field needs to be unique for each primary diagnosis in your raw data. Use the `Indexed_on` mapping to define the index field:

`primary_diagnoses.INDEX,{Indexed_on(submitted_primary_diagnosis_id)}`

If your schema doesn't contain any instances of a particular indexed field, you can specify `NONE`:
`{indexed_on(NONE)}`


## Transforming data using standard functions

In addition to mapping column names, you can also transform the values inside the cells to make them align with the schema. We've already seen the simplest case - the `single_val` function takes a single value for the named field and returns it (and should only be used when you expect one single value).

The standard functions are defined in `mappings.py`. They include functions for handling single values, list values, dates, and booleans.


## Writing your own custom functions

If the data cannot be transformed with one of the standard functions, you can define your own. In your data directory (the one that contains `manifest.yml`) create a python file (let's assume you called it `new_cohort.py`) and add the name of that file as the `mapping` entry in the manifest.

Following the format in the generic `mappings.py`, write your own functions in your python file for how to translate the data. To specify a custom mapping function in the template:

`primary_diagnoses.INDEX.basis_of_diagnosis,{new_cohort.custom_function(field_name)}`

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
