<!-- markdownlint-disable -->

<a href="../mappings.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `mappings.py`




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

<a href="../mappings.py#L25"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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

<a href="../mappings.py#L46"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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

<a href="../mappings.py#L61"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `has_value`

```python
has_value(data_values)
```

Returns a boolean based on whether the key in the mapping has a value. 


---

<a href="../mappings.py#L72"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `single_val`

```python
single_val(data_values)
```

Return the input as a single value. 



**Args:**
 
 - <b>`data_values`</b>:  a dict with values to be squashed 



**Returns:**
 A single value with any null values removed None if list is empty or contains only 'nan', 'NaN', 'NAN' 



**Raises:**
 MappingError if multiple values found 


---

<a href="../mappings.py#L101"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `list_val`

```python
list_val(data_values)
```

Takes a mapping with possibly multiple values from multiple sheets and returns an array of values. 



**Args:**
 
 - <b>`data_values`</b>:  a values dict 



**Returns:**
 a list of the data values 


---

<a href="../mappings.py#L122"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `pipe_delim`

```python
pipe_delim(data_values)
```

Takes a string and splits it into an array based on a pipe delimiter. 



**Args:**
 
 - <b>`data_values`</b>:  single pipe-delimited string 



**Returns:**
 a list of strings split by pipe 


---

<a href="../mappings.py#L137"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `placeholder`

```python
placeholder(data_values)
```

Return a dict with a placeholder key. 


---

<a href="../mappings.py#L142"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `index_val`

```python
index_val(data_values)
```

Take a mapping with possibly multiple values from multiple sheets and return an array. 


---

<a href="../mappings.py#L155"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `flat_list_val`

```python
flat_list_val(data_values)
```

Take a list mapping and break up any stringified lists into multiple values in the list. 


---

<a href="../mappings.py#L169"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `concat_vals`

```python
concat_vals(data_values)
```

Concatenate several data values 



**Args:**
 
 - <b>`data_values`</b>:  a list of values 



**Returns:**
 A concatenated string 


---

<a href="../mappings.py#L184"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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

<a href="../mappings.py#L204"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `integer`

```python
integer(data_values)
```

Convert a value to an integer. 


---

<a href="../mappings.py#L216"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `float_val`

```python
float_val(data_values)
```

Convert a value to a float. 



**Args:**
 
 - <b>`data_values`</b>:  A values dict 



**Returns:**
 A string or integer converted to a float or None if null value 



**Raises:**
 ValueError by float() if it cannot convert to float. 


---

<a href="../mappings.py#L249"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `ontology_placeholder`

```python
ontology_placeholder(data_values)
```

Placeholder function to make a fake ontology entry. 

Should only be used for testing. 



**Args:**
 
 - <b>`data_values`</b>:  a string value representing an ontology label 



**Returns:**
 a dict of the format 
 - <b>`{"id"`</b>:  "placeholder", 
 - <b>`"label"`</b>:  data_values} 


---

<a href="../mappings.py#L273"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `indexed_on`

```python
indexed_on(data_values)
```

Default indexing value for arrays. 



**Args:**
 
 - <b>`data_values`</b>:  a dict of the format 
 - <b>`{'<identifier_field>'`</b>: {'<sheet_name>':['<identifier>']}} 



**Returns:**
 a dict of the format 
 - <b>`{"field"`</b>:  <identifier_field>, 
 - <b>`"sheet_name"`</b>:  <sheet_name>, 
 - <b>`"values"`</b>:  [<identifiers>]} 


---

<a href="../mappings.py#L296"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `moh_indexed_on_donor_if_others_absent`

```python
moh_indexed_on_donor_if_others_absent(data_values)
```

Maps an object to a donor if not otherwise linked. 

Specifically for the FollowUp object which can be linked to multiple objects. 



**Args:**
 
 - <b>`data_values`</b>:  dict with lists of identifiers 



**Returns:**
 a dict of the format 
 - <b>`{"field"`</b>:  <field>, 
 - <b>`"sheet"`</b>:  <sheet>, 
 - <b>`"values"`</b>:  [<identifier or None>, <identifier or None>...]} Where the 'values' list contains a donor identifier if it should be linked to that donor or None if already linked to another object. 


---

## <kbd>class</kbd> `MappingError`




<a href="../mappings.py#L16"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(value)
```











---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
