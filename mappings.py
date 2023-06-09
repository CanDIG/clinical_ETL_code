import ast
import dateparser

MODULES = {}
IDENTIFIER = {}
VERBOSE = False


def warn(message):
    global VERBOSE
    global IDENTIFIER
    if VERBOSE:
        print(f"WARNING for {IDENTIFIER}: {message}")


class MappingError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        global IDENTIFIER
        if 'id' in IDENTIFIER:
            return repr(f"Check the values for {IDENTIFIER['id']} in {IDENTIFIER}: {self.value}")
        return repr(f"{IDENTIFIER} {self.value}")


# Format a date field to ISO standard
def date(data_values):
    raw_date = list_val(data_values)
    dates = []
    if raw_date is None:
        return None
    for date in raw_date:
        try:
            d = dateparser.parse(date, settings={'TIMEZONE': 'UTC'})
            dates.append(d.date().isoformat())
        except Exception as e:
            raise MappingError(f"error in date({raw_date}): {type(e)} {e}")
    return dates

# Single date
def single_date(data_values):
    dates = date(data_values)
    if len(dates) > 0:
        return dates[0]
    return None


# Returns a boolean based on whether or not the key in the mapping has a value
def has_value(data_values):
    if len(data_values.keys()) == 0:
        warn(f"no values passed in")
    else:
        key = list(data_values.keys())[0]
        if not is_null(data_values[key]):
            return True
    return False


# No matter how many items are registered with this key, squash to one
def single_val(data_values):
    all_items = list_val(data_values)
    if len(all_items) == 0:
        return None
    if len(set(all_items)) > 1:
        raise MappingError(f"More than one value was found for {list(data_values.keys())[0]} in {data_values}")
    return all_items[0]


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


# Convenience function to convert nan to boolean
def is_null(cell):
    if cell == 'nan' or cell is None or cell == '':
        return True
    return False

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