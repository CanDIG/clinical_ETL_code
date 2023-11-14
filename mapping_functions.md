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

Here, `primary_diagnoses` will be added as an array for the Donor with `submitter_donor_id`. Each entry in `primary_diagnoses` will use the values on the `PRIMARY_DIAGNOSES_SHEET` that have the same `submitter_donor_id`.

If your schema doesn't contain any instances of a particular indexed field, you can specify `NONE`:
`{indexed_on(NONE)}`

If your schema requires more complex mapping calculations, you can define an index function in your mapping file. The result of this index function should have the same shape as mappings.indexed_on:
```
{
  "sheet": sheet,
  "field": field,
  "values": [array of calculated values to use on the sheet.field]
}
```


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

# Standard Functions Index

# <kbd>module</kbd> `mappings`




**Global Variables**
---------------
- **VERBOSE**
- **MODULES**
- **IDENTIFIER_FIELD**
- **IDENTIFIER**
- **INDEX_STACK**
- **INDEXED_DATA**
- **CURRENT_LINE**
- **OUTPUT_FILE**

---

## <kbd>function</kbd> `date`

```python
date(data_values)
```

Format a list of dates to ISO standard YYYY-MM 

Parses a list of strings representing dates into a list of strings with dates in ISO format YYYY-MM. 



**Args:**
 
 - <b>`data_values`</b>:  a value dict with a list of date-like strings 



**Returns:**
 a list of dates in YYYY-MM format or None if blank/empty/unparseable 


---

## <kbd>function</kbd> `single_date`

```python
single_date(data_values)
```

Parses a single date to YYYY-MM format. 



**Args:**
 
 - <b>`data_values`</b>:  a value dict with a date 



**Returns:**
 a string of the format YYYY-MM, or None if blank/unparseable 


---

## <kbd>function</kbd> `has_value`

```python
has_value(data_values)
```

Returns a boolean based on whether the key in the mapping has a value. 


---

## <kbd>function</kbd> `single_val`

```python
single_val(data_values)
```

Parse a values dict and return the input as a single value. 



**Args:**
 
 - <b>`data_values`</b>:  a dict with values to be squashed 



**Returns:**
 A single value with any null values removed None if list is empty or contains only 'nan', 'NaN', 'NAN' 



**Raises:**
 MappingError if multiple values found 


---

## <kbd>function</kbd> `list_val`

```python
list_val(data_values)
```

Takes a mapping with possibly multiple values from multiple sheets and returns an array of values. 



**Args:**
 
 - <b>`data_values`</b>:  a values dict with a list of values 

**Returns:**
 The list of values 


---

## <kbd>function</kbd> `pipe_delim`

```python
pipe_delim(data_values)
```

Takes a string and splits it into an array based on a pipe delimiter. 



**Args:**
 
 - <b>`data_values`</b>:  values dict with single pipe-delimited string, e.g. "a|b|c" 



**Returns:**
 a list of strings split by pipe, e.g. ["a","b","c"] 


---

## <kbd>function</kbd> `placeholder`

```python
placeholder(data_values)
```

Return a dict with a placeholder key. 


---

## <kbd>function</kbd> `index_val`

```python
index_val(data_values)
```

Take a mapping with possibly multiple values from multiple sheets and return an array. 


---

## <kbd>function</kbd> `flat_list_val`

```python
flat_list_val(data_values)
```

Take a list mapping and break up any stringified lists into multiple values in the list. 

Attempts to use ast.literal_eval() to parse the list, uses split(',') if this fails. 



**Args:**
 
 - <b>`data_values`</b>:  a values dict with a stringified list, e.g. "['a','b','c']" 

**Returns:**
 A parsed list of items in the list, e.g. ['a', 'b', 'c'] 


---

## <kbd>function</kbd> `concat_vals`

```python
concat_vals(data_values)
```

Concatenate several data values 



**Args:**
 
 - <b>`data_values`</b>:  a values dict with a list of values 



**Returns:**
 A concatenated string 


---

## <kbd>function</kbd> `boolean`

```python
boolean(data_values)
```

Convert value to boolean. 



**Args:**
 
 - <b>`data_values`</b>:  A string to be converted to a boolean 



**Returns:**
 A boolean based on the input, `False` if value is in ["No", "no", "False", "false"] `None` if value is in [`None`, "nan", "NaN", "NAN"] `True` otherwise 


---

## <kbd>function</kbd> `integer`

```python
integer(data_values)
```

Convert a value to an integer. 



**Args:**
 
 - <b>`data_values`</b>:  a values dict with value to be converted to an int 

**Returns:**
 an integer version of the input value 

**Raises:**
 ValueError if int() cannot convert the input 


---

## <kbd>function</kbd> `float`

```python
float(data_values)
```

Convert a value to a float. 



**Args:**
 
 - <b>`data_values`</b>:  A values dict 



**Returns:**
 A values dict with a string or integer converted to a float or None if null value 



**Raises:**
 ValueError by float() if it cannot convert to float. 


---

## <kbd>function</kbd> `ontology_placeholder`

```python
ontology_placeholder(data_values)
```

Placeholder function to make a fake ontology entry. 

Should only be used for testing. 



**Args:**
 
 - <b>`data_values`</b>:  a values dict with a string value representing an ontology label 



**Returns:**
 a dict of the format: 
 - <b>`{"id"`</b>:  "placeholder","label": data_values} 


---

## <kbd>function</kbd> `indexed_on`

```python
indexed_on(data_values)
```

Default indexing value for arrays. 



**Args:**
 
 - <b>`data_values`</b>:  a values dict of identifiers to be indexed 



**Returns:**
 a dict of the format: 
 - <b>`{"field"`</b>:  <identifier_field>,"sheet_name": <sheet_name>,"values": [<identifiers>]} 


---

## <kbd>function</kbd> `moh_indexed_on_donor_if_others_absent`

```python
moh_indexed_on_donor_if_others_absent(data_values)
```

Maps an object to a donor if not otherwise linked. 

Specifically for the FollowUp object which can be linked to multiple objects. 



**Args:**
 
 - <b>`**data_values`</b>:  any number of values dicts with lists of identifiers, NOTE: values dict with donor identifiers must be specified first. 



**Returns:**
 a dict of the format: 


 - <b>`{'field'`</b>:  <field>, 'sheet': <sheet>, 'values': [<identifier or None>, <identifier or None>...]} 

Where the 'values' list contains a donor identifier if it should be linked to that donor or None if already linked to another object. 


---

## <kbd>class</kbd> `MappingError`




### <kbd>method</kbd> `MappingError.__init__`

```python
__init__(value)
```









