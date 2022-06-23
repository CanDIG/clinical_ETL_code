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
        return repr(f"Check the values for {IDENTIFIER['id']} in {IDENTIFIER}: {self.value}")


# Format a date field to ISO standard
def date(mapping):
    raw_date = list_val(mapping)
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


# Returns a boolean based on whether or not the key in the mapping has a value
def has_value(mapping):
    if len(mapping.keys()) == 0:
        warn(f"no values passed in")
    else:
        key = list(mapping.keys())[0]
        if not is_null(mapping[key]):
            return True
    return False


# No matter how many items are registered with this key, squash to one
def single_val(mapping):
    all_items = list_val(mapping)
    if len(all_items) == 0:
        return None
    if len(set(all_items)) > 1:
        raise MappingError(f"More than one value was found for {list(mapping.keys())[0]}")
    return all_items[0]


# Take a mapping with possibly multiple values from multiple sheets and return an array
def list_val(mapping):
    all_items = []
    if has_value(mapping):
        col = list(mapping.keys())[0]
        for sheet in mapping[col].keys():
            if "list" in str(type(mapping[col][sheet])):
                all_items.extend(mapping[col][sheet])
            else:
                all_items.append(mapping[col][sheet])
    return all_items


# Take a list mapping and break up any stringified lists into multiple values in the list
def flat_list_val(mapping):
    items = list_val(mapping)
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
