import ast
import dateparser
import json

VERBOSE = False
MODULES = {}
IDENTIFIER_FIELD = None
IDENTIFIER = None
INDEX_STACK = []
INDEXED_DATA = None
CURRENT_LINE = ""
OUTPUT_FILE = ""


class MappingError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        with open(f"{OUTPUT_FILE}_indexed.json", 'w') as f:
            json.dump(INDEXED_DATA, f, indent=4)
        return repr(f"Check the values for {IDENTIFIER} in {IDENTIFIER_FIELD}: {self.value}")


def date(data_values):
    """Format a list of dates to ISO standard YYYY-MM

    Parses a list of strings representing dates into a list of strings with dates in ISO format YYYY-MM.

    Args:
        data_values: a value dict with a list of date-like strings

    Returns:
        a list of dates in YYYY-MM format or None if blank/empty/unparseable
    """
    raw_date = list_val(data_values)
    dates = []
    if raw_date is None:
        return None
    for date in raw_date:
        dates.append(_parse_date(date))
    return dates


# Single date
def single_date(data_values):
    """Parses a single date to YYYY-MM format.

    Args:
        data_values: a value dict with a date

    Returns:
        a string of the format YYYY-MM, or None if blank/unparseable
    """
    val = single_val(data_values)
    if val is not None:
        return _parse_date(val)
    return None


def has_value(data_values):
    """Returns a boolean based on whether the key in the mapping has a value."""
    if len(data_values.keys()) == 0:
        _warn(f"no values passed in")
    else:
        key = list(data_values.keys())[0]
        if not _is_null(data_values[key]):
            return True
    return False


def single_val(data_values):
    """Parse a values dict and return the input as a single value.

    Args:
        data_values: a dict with values to be squashed

    Returns:
        A single value with any null values removed
        None if list is empty or contains only 'nan', 'NaN', 'NAN'

    Raises:
        MappingError if multiple values found
    """
    all_items = list_val(data_values)
    if len(all_items) == 0:
        return None
    all_items = set(all_items)
    if None in all_items:
        all_items.remove(None)
    if len(all_items) == 0:
        return None
    if len(all_items) > 1:
        raise MappingError(f"More than one value was found for {list(data_values.keys())[0]} in {data_values}")
    result = list(all_items)[0]
    if result is not None and result.lower() == 'nan':
        result = None
    return result


def list_val(data_values):
    """
    Takes a mapping with possibly multiple values from multiple sheets and returns an array of values.

    Args:
        data_values: a values dict with a list of values
    Returns:
        The list of values
    """
    all_items = []
    if has_value(data_values):
        col = list(data_values.keys())[0]
        for sheet in data_values[col].keys():
            if "list" in str(type(data_values[col][sheet])):
                all_items.extend(data_values[col][sheet])
            else:
                all_items.append(data_values[col][sheet])
    return all_items


def pipe_delim(data_values):
    """Takes a string and splits it into an array based on a pipe delimiter.

    Args:
         data_values: values dict with single pipe-delimited string, e.g. "a|b|c"

    Returns:
        a list of strings split by pipe, e.g. ["a","b","c"]
    """
    val = single_val(data_values)
    if val is not None:
        return val.split('|')
    return None


def placeholder(data_values):
    """Return a dict with a placeholder key."""
    return {"placeholder": data_values}


def index_val(data_values):
    """Take a mapping with possibly multiple values from multiple sheets and return an array."""
    all_items = []
    if has_value(data_values):
        col = list(data_values.keys())[0]
        for sheet in data_values[col].keys():
            if "list" in str(type(data_values[col][sheet])):
                all_items.extend(data_values[col][sheet])
            else:
                all_items.append(data_values[col][sheet])
    return all_items


def flat_list_val(data_values):
    """Take a list mapping and break up any stringified lists into multiple values in the list.

    Attempts to use ast.literal_eval() to parse the list, uses split(',') if this fails.

    Args:
        data_values: a values dict with a stringified list, e.g. "['a','b','c']"
    Returns:
        A parsed list of items in the list, e.g. ['a', 'b', 'c']
    """
    items = list_val(data_values)
    all_items = []
    for item in items:
        try:
            result = ast.literal_eval(item)
            if "list" in str(type(result)):
                all_items.extend(result)
        except Exception:
            all_items.extend(map(lambda x: x.strip(), item.split(",")))
    return all_items


def concat_vals(data_values):
    """Concatenate several data values

    Args:
        data_values: a values dict with a list of values

    Returns:
        A concatenated string
    """
    result = []
    for x in data_values:
        result.extend(data_values[x].values())
    return "_".join(result)


def boolean(data_values):
    """Convert value to boolean.

    Args:
        data_values: A string to be converted to a boolean

    Returns:
        A boolean based on the input,
        `False` if value is in ["No", "no", "False", "false"]
        `None` if value is in [`None`, "nan", "NaN", "NAN"]
        `True` otherwise
    """
    cell = single_val(data_values)
    if cell is None or cell.lower().strip() == "nan":
        return None
    if cell.lower().strip() == "no" or cell.lower().strip() == "false":
        return False
    return True


def integer(data_values):
    """Convert a value to an integer.

    Args:
        data_values: a values dict with value to be converted to an int
    Returns:
        an integer version of the input value
    Raises:
        ValueError if int() cannot convert the input
    """
    cell = single_val(data_values)
    if cell is None or cell.lower() == "nan":
        return None
    try:
        return int(cell)
    except ValueError as e:
        _warn(e)
        return None


def float(data_values):
    """Convert a value to a float.

    Args:
        data_values: A values dict

    Returns:
        A values dict with a string or integer converted to a float or None if null value

    Raises:
        ValueError by float() if it cannot convert to float.
    """
    cell = single_val(data_values)
    if cell is None or cell.lower() == "nan":
        return None
    try:
        return float(cell)
    except ValueError as e:
        _warn(e)
        return None


def ontology_placeholder(data_values):
    """Placeholder function to make a fake ontology entry.

    Should only be used for testing.

    Args:
        data_values: a values dict with a string value representing an ontology label

    Returns:
        a dict of the format:
        {"id": "placeholder","label": data_values}
    """
    if "str" in str(type(data_values)):
        return {
            "id": "placeholder",
            "label": data_values
        }
    return {
        "id": "placeholder",
        "label": single_val(data_values)
    }


def indexed_on(data_values):
    """Default indexing value for arrays.

    Args:
        data_values: a values dict of identifiers to be indexed

    Returns:
        a dict of the format:
        {"field": <identifier_field>,"sheet_name": <sheet_name>,"values": [<identifiers>]}
    """
    field = list(data_values.keys())[0]
    sheet = list(data_values[field].keys())[0]

    return {
        "field": field,
        "sheet": sheet,
        "values": data_values[field][sheet]
    }


def moh_indexed_on_donor_if_others_absent(data_values):
    """Maps an object to a donor if not otherwise linked.

    Specifically for the FollowUp object which can be linked to multiple objects.

    Args:
        **data_values: any number of values dicts with lists of identifiers, NOTE: values dict with donor identifiers
        must be specified first.

    Returns:
        a dict of the format:

            {'field': <field>, 'sheet': <sheet>, 'values': [<identifier or None>, <identifier or None>...]}

        Where the 'values' list contains a donor identifier if it should be linked to that donor or None if already
        linked to another object.
    """
    result = []
    field = list(data_values.keys())[0]
    sheet = list(data_values[field].keys())[0]

    for key in data_values:
        vals = list(data_values[key].values()).pop()
        for i in range(0, len(vals)):
            if len(result) <= i:
                result.append(None)
            if vals[i] is not None:
                if result[i] is None:
                    result[i] = vals[i]
                else:
                    result[i] = None
    return {
        "field": field,
        "sheet": sheet,
        "values": result
    }


def _warn(message):
    """Warns a user when a mapping is unsuccessful with the IDENTIFIER and FIELD."""
    global IDENTIFIER
    if IDENTIFIER is not None:
        print(f"WARNING for {IDENTIFIER_FIELD}={IDENTIFIER}: {message}")
    else:
        print(f"WARNING: {message}")


def _push_to_stack(sheet, id, rownum):
    INDEX_STACK.append(
        {
            "sheet": sheet,
            "id": id,
            "rownum": rownum
        }
    )
    if VERBOSE:
        print(f"Pushed to stack: {INDEX_STACK}")


def _pop_from_stack():
    if VERBOSE:
        print("Popped from stack")
    if len(INDEX_STACK) > 0:
        return INDEX_STACK.pop()
    else:
        return None


def _peek_at_top_of_stack():
    val = INDEX_STACK[-1]
    if VERBOSE:
        print(json.dumps(val, indent=2))
    return {
        "sheet": val["sheet"],
        "id": val["id"],
        "rownum": val["rownum"]
    }


def _is_null(cell):
    """Convert nan, None, '' to boolean."""
    if cell == 'nan' or cell is None or cell == '':
        return True
    return False


def _single_map(mapping, field):
    """Parse the contents for the specified field from the template."""
    return single_val({field: mapping[field]})


# Convenience function to parse dates to ISO format
def _parse_date(date_string):
    """
    Parses any date-like string into YYYY-MM format.

    Args:
        date_string: A string in various date formats

    Returns:
        A string in year, month ISO format: YYYY-MM

    Raises:
        MappingError if dateparser cannot recognise the date format.
    """
    if any(char in '0123456789' for char in date_string):
        try:
            d = dateparser.parse(date_string, settings={'TIMEZONE': 'UTC'})
            return d.date().strftime("%Y-%m")
        except Exception as e:
            raise MappingError(f"error in date({date_string}): {type(e)} {e}")
    return date_string
