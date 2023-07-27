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


class MappingError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(f"Check the values for {IDENTIFIER} in {IDENTIFIER_FIELD}: {self.value}")


# Format a date field to ISO standard
def date(data_values):
    raw_date = list_val(data_values)
    dates = []
    if raw_date is None:
        return None
    for date in raw_date:
        dates.append(_parse_date(date).date().isoformat())
    return dates


# Single date
def single_date(data_values):
    val = single_val(data_values)
    if val is not None:
        return _parse_date(val)
    return None


# Returns a boolean based on whether or not the key in the mapping has a value
def has_value(data_values):
    if len(data_values.keys()) == 0:
        _warn(f"no values passed in")
    else:
        key = list(data_values.keys())[0]
        if not _is_null(data_values[key]):
            return True
    return False


# No matter how many items are registered with this key, squash to one
def single_val(data_values):
    all_items = list_val(data_values)
    if len(all_items) == 0:
        return None
    if len(set(all_items)) > 1:
        raise MappingError(f"More than one value was found for {list(data_values.keys())[0]} in {data_values}")
    result = all_items[0]
    if result is not None and result.lower() == 'nan':
        result = None
    return result


# Take a mapping with possibly multiple values from multiple sheets and return an array
def list_val(data_values):
    all_items = []
    if has_value(data_values):
        col = list(data_values.keys())[0]
        for sheet in data_values[col].keys():
            if "list" in str(type(data_values[col][sheet])):
                all_items.extend(data_values[col][sheet])
            else:
                all_items.append(data_values[col][sheet])
    return all_items


def placeholder(data_values):
    return {"placeholder": data_values}

# Take a mapping with possibly multiple values from multiple sheets and return an array
def index_val(data_values):
    all_items = []
    if has_value(data_values):
        col = list(data_values.keys())[0]
        for sheet in data_values[col].keys():
            if "list" in str(type(data_values[col][sheet])):
                all_items.extend(data_values[col][sheet])
            else:
                all_items.append(data_values[col][sheet])
    return all_items


# Take a list mapping and break up any stringified lists into multiple values in the list
def flat_list_val(data_values):
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


# Convert various responses to boolean
def boolean(data_values):
    cell = single_val(data_values)
    if cell is None or cell.lower() == "nan":
        return None
    if cell.lower() == "no" or cell.lower == "false":
        return False
    return True


def integer(data_values):
    cell = single_val(data_values)
    if cell is None or cell.lower() == "nan":
        return None
    try:
        return int(cell)
    except:
        return None


# Placeholder function to make a fake ontology entry
def ontology_placeholder(data_values):
    if "str" in str(type(data_values)):
        return {
            "id": "placeholder",
            "label": mapping
        }
    return {
        "id": "placeholder",
        "label": single_val(data_values)
    }


# Default indexing value for arrays
def indexed_on(data_values):
    result = set()
    for key in data_values:
        for item in data_values[key]:
            result = result.union(data_values[key][item])

    # remove any Nones or nans
    final = []
    for i in result:
        if i is not None and str(i).lower() != 'nan':
            final.append(i)
    return final


def _warn(message):
    global VERBOSE
    global IDENTIFIER
    if VERBOSE:
        print(f"WARNING for {IDENTIFIER_FIELD}={IDENTIFIER}: {message}")


def _push_to_stack(id, value, indiv):
    INDEX_STACK.append(
        {
            "id": id,
            "value": value,
            "indiv": indiv
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
        "id": val["id"],
        "value": val["value"],
        "indiv": val["indiv"]
    }


# Convenience function to convert nan to boolean
def _is_null(cell):
    if cell == 'nan' or cell is None or cell == '':
        return True
    return False

# Convenience function to parse dates to ISO format
def _parse_date(date_string):
    if any(char in '0123456789' for char in date_string):
        try:
            d = dateparser.parse(date_string, settings={'TIMEZONE': 'UTC'})
            return d.date().isoformat()
        except Exception as e:
            raise MappingError(f"error in date({date_string}): {type(e)} {e}")
    return date_string
