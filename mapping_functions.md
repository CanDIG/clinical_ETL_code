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

For cases where there can be multiple instances of a schema (e.g. multiple treatments, or specimens), you _must_ specify an indexing field for that schema.

## Transforming data using standard functions

In addition to mapping column names, you can also transform the values inside the cells to make them align with the schema. We've already seen the simplest case - the `single_val` function takes a single value for the named field and returns it. 

The standard functions are defined in `mappings.py`. They include functions for handling single values, list values, dates, and booleans. 

## Writing your own custom functions

If the data cannot be transformed with one of the standard functions, you can define your own. In your data directory (the one that contains `manifest.yml`) create a python file and add the name of that file as the `mapping` entry in the manifest. 

- Entries that end with `INDEX` in the name represent arrays: if there are subsequent entries after the first line ending with `INDEX`, this represents an array of dicts. The first entry ending in `INDEX` can be mapped to an index field using the `{indexed_on(FIELD)}` notation. Any subsequent subentries in the dict will be mapped into the corresponding dict in the array.

```
prop_a.INDEX
prop_a.INDEX.prop_b
prop_a.INDEX.prop_c

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

## Defining mapping functions



## Implementing custom functions

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
