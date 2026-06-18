# mappings and validation based on the mohccn schema

import requests
import yaml
import json
import re
from copy import deepcopy
import jsonschema
from collections import Counter
import openapi_spec_validator as osv


class ValidationError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(f"Validation error: {self.value}")

"""
Convenience methods for validating openapi as jsonschema
"""

def openapi_to_jsonschema(schema_text, schema_name):
    # save off all the component schemas into a "defs" component that can be passed into a jsonschema validation
    defs_set = set()
    schema_text = schema_text.split("\n")
    for i in range(0, len(schema_text)):
        ref_match = re.match(r"(.*\$ref:).*(#/components/schemas/.+)$", schema_text[i])
        if ref_match is not None:
            schema_text[i] = schema_text[i].replace("#/components/schemas/", "#/$defs/")
            defs_set.add(ref_match.group(2).strip('\"').strip("\'").replace("#/components/schemas/", ""))

    openapi_components = yaml.safe_load("\n".join(schema_text))["components"]["schemas"]
    # populate defs for jsonschema
    defs = {}
    for d in defs_set:
        defs[d] = openapi_components[d]

    json_schema = deepcopy(openapi_components[schema_name])
    json_schema["$defs"] = defs
    return json_schema

"""
Base class to represent a Katsu OpenAPI schema for ETL.
"""

class BaseSchema:
    # The component name in the OpenAPI specification
    schema_name = None

    # Values that count as "empty" for per-donor completeness scoring.
    # NOTE: "Not available" is intentionally NOT included: it is treated as a
    # valid, complete answer for completeness purposes. (This differs from the
    # required_but_missing / cases_missing_data stats in validate_schema, which
    # still treat "Not available" as missing.)
    EMPTY_VALUES = (None, "")

    # schema for validation beyond jsonschema checks. Each schema that is described in the model gets an entry.
    validation_schema = {
        "examples": {             # There should be a method `validate_examples` implemented to validate conditionals
            "id": "example_id",  # The id used to disambiguate instances of the schema. If None, an array index is used
            "name": "Example",   # The proper name for the schema
            "required_fields": [ # Any fields specified as required in the model (but not absolutely necessary for jsonschema)
                "example_id",
                "attribute_1"
            ],
            "nested_schemas": [  # Any schema instances that may be nested within instances of this schema.
                "more_examples"      # Nested instances will be validated as part of the validation of the parent.
            ]
        },
        "more_examples": {
            "id": None,
            "name": "Example 2",
            "required_fields": [],
            "nested_schemas": []
        }
    }


    def __init__(self, url, simple=False):
        self.validation_warnings = []
        self.validation_errors = []
        self.statistics = {}
        self.identifiers = {}
        self.stack_location = []
        self.schema = {}
        self.openapi_url = url
        self.json_schema = None
        self.template = None
        self.katsu_sha = None
        self.scaffold = None

        """Retrieve the schema from the supplied URL, return as dictionary."""
        try:
            osv.validate_url(self.openapi_url)
            resp = requests.get(self.openapi_url)
            resp.raise_for_status()
            schema = yaml.safe_load(resp.text)
        except Exception as e:
            print("Error reading the openapi schema, please ensure you have provided a url to a valid openapi schema.")
            print(e)
            return

        self.schema = schema["components"]["schemas"]
        sha_match = re.match(r".+Based on commit \"(.+)\".*", schema["info"]["description"])
        if sha_match is not None:
            self.katsu_sha = sha_match.group(1)
        else:
            sha_match = re.match(r".+Based on http.*katsu\/(.+)\/chord_metadata_service.*", schema["info"]["description"])
            if sha_match is not None:
                self.katsu_sha = sha_match.group(1)

        self.json_schema = openapi_to_jsonschema(resp.text, self.schema_name)

        # create the template for the schema_name schema
        self.scaffold = self.generate_schema_scaffold(self.schema[self.schema_name], list(self.validation_schema.keys())[0])
        # print(json.dumps(self.scaffold, indent=4))
        _, raw_template = self.generate_mapping_template(self.scaffold, node_name=f"{self.base_name}.INDEX")

        # add default mapping functions:
        self.template = self.add_default_mappings(raw_template)


    def warn(self, message, conditional_required=True):
        """Record a validation warning.

        `conditional_required` (default True) marks the warning as indicating a
        required or conditionally-required field/object that is missing, so it
        counts against per-donor 'fulsome' completeness. Set it False for soft
        notes and cross-field consistency warnings that are not about a missing
        requirement. The warning is attributed to the current donor via
        stack_location[0] so the completeness engine can look it up."""
        prefix = " > ".join(self.stack_location)
        if prefix.strip() == "":
            prefix = ""
        else:
            prefix += ": "
        message = prefix + message
        self.validation_warnings.append(f"{message}")
        if conditional_required and self.stack_location:
            donor = self.stack_location[0]
            if not hasattr(self, "_conditional_gaps"):
                self._conditional_gaps = {}
            self._conditional_gaps.setdefault(donor, []).append(message)


    def fail(self, message):
        prefix = " > ".join(self.stack_location)
        if prefix.strip() == "":
            prefix = ""
        else:
            prefix += ": "
        message = prefix + message
        self.validation_errors.append(f"{message}")


    def expand_ref(self, ref, validation_schema_node):
        if "$ref" in ref:
            refName = ref["$ref"].replace("#/components/schemas/", "")
            return self.generate_schema_scaffold(json.loads(json.dumps(self.schema[refName])), validation_schema_node)
        return ref["type"]


    def generate_schema_scaffold(self, schema_obj, validation_schema_node):
        result = {}
        if "type" in schema_obj:
            if schema_obj["type"] == "object":
                for prop in schema_obj["properties"]:
                    prop_obj = self.generate_schema_scaffold(schema_obj["properties"][prop], prop)
                    result[prop] = prop_obj
                if validation_schema_node in self.validation_schema:
                    nested_schemas = {}
                    for schema in self.validation_schema[validation_schema_node]["nested_schemas"]:
                        if schema in result:
                            nested_schemas[schema] = result.pop(schema)
                    for schema in nested_schemas:
                        result[schema] = nested_schemas[schema]
            elif schema_obj["type"] == "array":
                result = [self.generate_schema_scaffold(schema_obj["items"], validation_schema_node)]
            else:
                result = schema_obj["type"]
        elif "$ref" in schema_obj:
            result = self.expand_ref(schema_obj, validation_schema_node)
        elif "allOf" in schema_obj:
            result = self.expand_ref(schema_obj["allOf"][0], validation_schema_node)
        elif "oneOf" in schema_obj:
            result = self.expand_ref(schema_obj["oneOf"][0], validation_schema_node)
        elif "anyOf" in schema_obj:
            result = self.expand_ref(schema_obj["anyOf"][0], validation_schema_node)
        else:
            result = "unknown"
        return result


    def generate_mapping_template(self, node, node_name="", node_names=None):
        """Create a template for the schema, for use with the --template flag."""
        if node_names is None:
            node_names = []
        if "str" in str(type(node)):
            node_names.append(f"{node_name},")
            return "string", node_names
        elif "list" in str(type(node)):
            new_node_name = ".".join((node_name, "INDEX"))
            sc, nn = self.generate_mapping_template(node[0], new_node_name, node_names)
            return [sc], nn
        elif "number" in str(type(node)) or "integer" in str(type(node)):
            return 0, node_names
        elif "boolean" in str(type(node)):
            return True, node_names
        elif "dict" in str(type(node)):
            scaffold = {}
            node_names.append(f"{node_name},")
            for prop in node.keys():
                if node_name == "":
                    new_node_name = prop
                else:
                    new_node_name = ".".join((node_name, prop))
                scaffold[prop], node_names = self.generate_mapping_template(node[prop], new_node_name, node_names)
            return scaffold, node_names
        else:
            return str(type(node)), node_names
        return None, node_names


    def add_default_mappings(self, template):
        # if line ends in INDEX, use indexed_on
        # otherwise, single_val
        result = []
        index_stack = []
        sheet_stack = []
        for i in range(0, len(template)):
            # work with line w/o comma
            x = template[i]
            if x.startswith("##"):
                continue

            x_match = re.match(r"(.+),", x)
            if x_match is not None:
                field = x_match.group(1)
                field_bits = field.split(".")
                data_value = field_bits[-1]

                # adjust the size of the stack: if it's bigger than the number of INDEX in the line, trim the stack back
                num_indices = field_bits.count("INDEX")
                if len(index_stack) > num_indices:
                    index_stack = index_stack[0:num_indices]
                    sheet_stack = sheet_stack[0:num_indices]

                if data_value == "INDEX":
                    # base case: assume that the index_value is the last bit before the index
                    index_value = field_bits[len(field_bits)-2]

                    # clean up the sheet stack: are the last sheets still involved?
                    if len(sheet_stack) > 1:
                        while 1:
                            last_sheet = sheet_stack.pop()
                            if last_sheet == f"{self.base_name}_SHEET" or last_sheet.replace("_SHEET", "").lower() in field:
                                sheet_stack.append(last_sheet)
                                break

                    sheet_stack.append(f"{index_value.upper()}_SHEET")
                    temp = index_value.lower()
                    if f"{temp}s" in self.validation_schema:
                        temp = f"{temp}s"
                    index_value = self.validation_schema[temp]["id"]

                    # next case: data value could be the the next line's last bit:
                    next_line = template[i+1]
                    next_match = re.match(r"(.+),", next_line)
                    next_bits = next_match.group(1).split(".")
                    if field in next_line:
                        # this index is NOT a nested entry of the prev one; we need to figure out how far back to un-nest.
                        if len(index_stack) > 0:
                            prev_line = template[i-1]
                            if field not in prev_line:
                                prev_match = re.match(r"(.+),", prev_line)
                                prev_bits = prev_match.group(1).split(".")

                                # if the previous line has more indices than we have now, we have to trim the index_stack.
                                if prev_bits.count("INDEX") >= num_indices:
                                    # if prev_bits does not end on INDEX, needs to be trimmed back to its last INDEX:
                                    if prev_bits[-1] != "INDEX":
                                        while len(prev_bits) > 0:
                                            if prev_bits[-1] != "INDEX":
                                                prev_bits.pop()
                                            elif prev_bits.count("INDEX") > num_indices:
                                                prev_bits.pop()
                                            else:
                                                break

                                    # we need to figure out just how far back these differ:
                                    count = 0
                                    while 1:
                                        # if this is now the same, we're done
                                        if (".".join(prev_bits) == ".".join(field_bits)):
                                            break
                                        count += 1
                                        # bounce off the last two bits from field_bits and prev_bits
                                        field_bits.pop()
                                        field_bits.pop()
                                        prev_bits.pop()
                                        prev_bits.pop()

                                    # pop off {count} from index_stack, but stop as soon as we have fewer than the number of indices
                                    for i in range(0, count):
                                        if len(index_stack) < num_indices:
                                            break
                                        index_stack.pop()

                        # this should be added to the stack, but not if the value is "INDEX"
                        if index_value is not None and index_value != "INDEX":
                            index_stack.append(index_value)
                            if len(index_stack) > 1:
                                index_value = index_stack[-2]
                        else:
                            index_value = index_stack[-1]
                    else:
                        sheet_stack.pop()
                    x += f" {{indexed_on({sheet_stack[-1]}.{index_value})}}"
                elif data_value.endswith("day_interval") or data_value.endswith("month_interval"):
                    continue
                elif data_value.endswith("_not_available"):
                    x += f" {{numeric_not_available({sheet_stack[-1]}.{'_'.join(data_value.split('_')[:-2])})}}"
                elif data_value.endswith("date") or data_value.startswith("date") and data_value != "date_resolution":
                    x += f" {{date_interval({sheet_stack[-1]}.{data_value})}}"
                elif data_value.startswith("number_") or data_value.startswith("age_") or "_per_" in data_value \
                        or data_value in ["ca125", "cea", "psa_level", "radiation_therapy_dosage",
                                          "radiation_therapy_fractions", "pack_years_smoked"] or \
                        "cycle" in data_value:
                    x += f" {{integer({sheet_stack[-1]}.{data_value})}}"
                elif "cumulative" in data_value or "_percent_" in data_value or \
                        data_value in ["greatest_dimension_tumour", "tumour_length", "tumour_width"]:
                    x += f" {{floating({sheet_stack[-1]}.{data_value})}}"
                elif data_value in ["treatment_type", "hpv_strain", "tobacco_type"] or "progression" in data_value or \
                        data_value.startswith("margin_types"):
                    x += f" {{pipe_delim({sheet_stack[-1]}.{data_value})}}"
                else:
                    x += f" {{single_val({sheet_stack[-1]}.{data_value})}}"
                result.append(x)
        return result

    def validate_ingest_map(self, map_json):
        self.statistics["required_but_missing"] = {}
        self.statistics["schemas_used"] = []
        self.statistics["cases_missing_data"] = []
        self.statistics["donor_completeness"] = {}
        self._conditional_gaps = {}   # donor_id -> [conditional-requirement warnings]

        for key in self.validation_schema.keys():
            self.validation_schema[key]["extra_args"] = {
                "index": 0
            }
        root_schema = list(self.validation_schema.keys())[0]
        for x in range(0, len(map_json[root_schema])):
            self.validate_jsonschema(map_json[root_schema][x], x)
            self.validate_schema(root_schema, map_json[root_schema][x])
            record = self.calculate_donor_completeness(map_json[root_schema][x])
            if record is not None:
                self.statistics["donor_completeness"][record["donor_id"]] = record
        for schema in self.identifiers:
            most_common = self.identifiers[schema].most_common()
            if most_common[0][1] > 1:
                for x in most_common:
                    if x[1] > 1:
                        self.fail(f"Duplicated IDs: in schema {schema}, {x[0]} occurs {x[1]} times")
        self.statistics["schemas_not_used"] = list(set(self.validation_schema.keys()) - set(self.statistics["schemas_used"]))
        self.statistics["summary_cases"] = {
            "complete_cases": len(map_json[root_schema]) - len(self.statistics["cases_missing_data"]),
            "total_cases": len(map_json[root_schema])
        }


    def validate_jsonschema(self, map_json, index):
        for error in jsonschema.Draft202012Validator(self.json_schema).iter_errors(map_json):
            id_field = self.validation_schema[list(self.validation_schema.keys())[0]]["id"]

            # is this error a None where it's nullable?
            if error.instance is None and 'nullable' in error.schema and error.schema['nullable'] == True:
                pass # this was too hard to write as a negative statement, so the error is in the else
            else:
                root_schema = list(self.validation_schema.keys())[0]
                location = [f"{self.validation_schema[root_schema]['name']} {index}"]
                if id_field in map_json:
                    location = [map_json[id_field]]
                    curr_map = map_json
                    while len(error.path) > 1:
                        node = error.path.popleft()
                        if "str" in str(type(node)):
                            curr_map = curr_map[node]
                            idx = error.path.popleft()
                            if "str" in str(type(idx)):
                                error.path.appendleft(idx)
                                continue
                            # is there an id for this?
                            curr_map = curr_map[idx]
                            if node in self.validation_schema:
                                sch = self.validation_schema[node]
                                if "id" in sch and sch["id"] is not None and sch["id"] in curr_map:
                                    id_field = curr_map[sch["id"]]
                                else:
                                    id_field = f"{node}[{idx}]"
                            else:
                                id_field = node
                            location.append(f"{id_field}")
                    if len(error.path) > 0:
                        location.append(error.path.popleft())
                message = f"{' > '.join(location)}: {error.message}"
                self.fail(message)


    def validate_schema(self, schema_name, map_json):
        id = f"{self.validation_schema[schema_name]['name']} {self.validation_schema[schema_name]['extra_args']['index']}"
        if self.validation_schema[schema_name]["id"] is not None and self.validation_schema[schema_name]["id"] in map_json:
            id = map_json[self.validation_schema[schema_name]["id"]]
            if schema_name not in self.identifiers:
                self.identifiers[schema_name] = Counter()
            self.identifiers[schema_name].update([id])
        required_fields = self.validation_schema[schema_name]["required_fields"]
        nested_schemas = self.validation_schema[schema_name]["nested_schemas"]
        self.stack_location.append(str(id))
        case = self.stack_location[0]

        # print(f"Validating schema {schema_name} for {self.stack_location[-1]}")
        if schema_name not in self.statistics["required_but_missing"]:
            self.statistics["required_but_missing"][schema_name] = {}
        if schema_name not in self.statistics["schemas_used"]:
            self.statistics["schemas_used"].append(schema_name)

        remove_these = []
        for f in required_fields:
            if f not in self.statistics["required_but_missing"][schema_name]:
                self.statistics["required_but_missing"][schema_name][f] = {
                    "total": 0,
                    "missing": 0
                }
            self.statistics["required_but_missing"][schema_name][f]["total"] += 1
            if f not in map_json or map_json[f] == "Not available":
                # Flat required-field gaps are handled by the completeness
                # engine's _required_complete (which, unlike this check, treats
                # "Not available" as a valid value), so don't double-count here.
                self.warn(f"{f} required for {schema_name}", conditional_required=False)
                self.statistics["required_but_missing"][schema_name][f]["missing"] += 1
                if case not in self.statistics["cases_missing_data"]:
                    self.statistics["cases_missing_data"].append(case)
                if f not in map_json:
                    map_json[f] = None
                    remove_these.append(f)

        eval(f"self.validate_{schema_name}({map_json})")
        for f in remove_these:
            map_json.pop(f)

        for ns in nested_schemas:
            if ns in map_json:
                for x in range(0, len(map_json[ns])):
                    self.validation_schema[ns]["extra_args"]["index"] = x
                    if "list" in str(type(map_json[ns])):
                        self.validate_schema(ns, map_json[ns][x])
                    else:
                        self.validate_schema(ns, map_json[ns])
        self.stack_location.pop()

    # ------------------------------------------------------------------ #
    # Per-donor completeness                                             #
    # ------------------------------------------------------------------ #
    # Two orthogonal axes per donor:
    #   * tier  ("A"/"B"/None) -- driven by sample_registration composition
    #   * level ("fulsome"/"minimal"/"incomplete") -- driven by field validity
    # A schema subclass opts in by defining `tier_criteria`, `minimal_criteria`
    # and (optionally) `conditional_fields` plus the `_sample_kind` classifier.
    # Schemas that don't define these get None (feature disabled for them).

    def _field_present(self, obj, field):
        """True if `field` has a non-empty value on `obj`.

        "Not available" counts as a valid, complete value (see EMPTY_VALUES)."""
        return isinstance(obj, dict) and field in obj and obj[field] not in self.EMPTY_VALUES

    def _find_objects(self, node, key):
        """Return every object appearing under `key` anywhere in the donor tree."""
        found = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k == key:
                    found.extend(v if isinstance(v, list) else [v])
                found.extend(self._find_objects(v, key))
        elif isinstance(node, list):
            for item in node:
                found.extend(self._find_objects(item, key))
        return [o for o in found if isinstance(o, dict)]

    def _evaluate_tier(self, donor):
        """Classify a donor's sample composition into a single, exclusive tier.

        Tier criteria are cumulative (Tier A's samples are a superset of Tier B's),
        so a donor that qualifies for A also qualifies for B. The returned `tier`
        resolves this in favour of the highest tier, so a Tier A donor is counted
        ONLY as A and never toward the Tier B total. The `criteria_met` dict is
        diagnostic (overlapping) and must not be used for tallying totals."""
        samples = self._find_objects(donor, "sample_registrations")
        counts = {}
        for s in samples:
            kind = self._sample_kind(s)
            if kind:
                counts[kind] = counts.get(kind, 0) + 1
        criteria_met = {
            tier: all(counts.get(k, 0) >= n for k, n in req.items())
            for tier, req in self.tier_criteria.items()
        }
        # highest satisfied tier wins; assumes tier_criteria ordered strongest-first
        tier = next((t for t in self.tier_criteria if criteria_met.get(t)), None)
        return tier, counts, criteria_met

    def _evaluate_minimal(self, donor):
        """Check the reduced 'minimal' field set on every existing instance."""
        unmet = []
        for schema_name, fields in self.minimal_criteria.items():
            instances = [donor] if schema_name == self._root_schema() \
                else self._find_objects(donor, schema_name)
            id_key = self.validation_schema.get(schema_name, {}).get("id")
            for inst in instances:
                ident = inst.get(id_key, "?") if id_key else "?"
                unmet += [f"{schema_name}[{ident}].{f}"
                          for f in fields if not self._field_present(inst, f)]
        return (len(unmet) == 0), unmet

    def _required_complete(self, schema_name, obj, unmet, prefix=""):
        """Recursively check all required_fields across the donor tree."""
        spec = self.validation_schema[schema_name]
        id_key = spec["id"]
        ident = obj.get(id_key, "?") if id_key else "?"
        here = f"{prefix}{schema_name}[{ident}]"
        for f in spec["required_fields"]:
            if not self._field_present(obj, f):
                unmet.append(f"{here}.{f}")
        for ns in spec["nested_schemas"]:
            for child in (obj.get(ns) or []):
                self._required_complete(ns, child, unmet, prefix=f"{here} > ")

    def _evaluate_required_instances(self, donor):
        """Check that required nested objects exist (e.g. >= 1 treatment).

        Driven by the optional `required_instances` list on the schema subclass,
        each entry being {"key": <json key>, "min": <count>}. Objects are counted
        anywhere in the donor tree via _find_objects."""
        unmet = []
        for spec in getattr(self, "required_instances", []):
            found = len(self._find_objects(donor, spec["key"]))
            need = spec.get("min", 1)
            if found < need:
                unmet.append(
                    f"missing required object: {spec['key']} (found {found}, need >= {need})")
        return unmet

    def _evaluate_fulsome(self, donor, donor_id):
        """Fulsome = every required field present (across the whole tree) AND
        every conditionally-required field/object present.

        Flat required fields are checked directly by _required_complete (which
        honours "Not available" as a valid value). The conditional requirements
        are taken from the validation pass itself: every `warn(...)` raised with
        conditional_required=True during this donor's validation is a missing
        conditional requirement. This means *all* conditional rules in the
        validate_* methods are covered automatically and stay in sync as the
        model evolves -- no rule needs to be re-listed here.

        NOTE: relies on validate_schema having run for this donor first (it does,
        in validate_ingest_map, immediately before calculate_donor_completeness)."""
        unmet = []
        self._required_complete(self._root_schema(), donor, unmet)
        unmet += getattr(self, "_conditional_gaps", {}).get(donor_id, [])
        unmet += self._evaluate_required_instances(donor)
        return (len(unmet) == 0), unmet

    def _root_schema(self):
        return list(self.validation_schema.keys())[0]

    def calculate_donor_completeness(self, donor):
        """Return a per-donor completeness record, or None if this schema does
        not define completeness criteria."""
        if getattr(self, "tier_criteria", None) is None \
                or getattr(self, "minimal_criteria", None) is None:
            return None

        id_field = self.validation_schema[self._root_schema()]["id"]
        donor_id = donor.get(id_field)
        tier, sample_counts, tier_criteria_met = self._evaluate_tier(donor)
        minimal_ok, minimal_unmet = self._evaluate_minimal(donor)
        # conditional gaps are keyed by stack_location[0] == str(donor_id)
        fulsome_ok, fulsome_unmet = self._evaluate_fulsome(donor, str(donor_id))
        level = "fulsome" if fulsome_ok else "minimal" if minimal_ok else "incomplete"
        return {
            "donor_id": donor_id,
            "tier": tier,                       # "A" / "B" / None (exclusive)
            "level": level,                     # fulsome / minimal / incomplete
            "type": (f"Tier {tier} {level}" if tier else f"untiered {level}"),
            "tier_criteria_met": tier_criteria_met,  # diagnostic only (overlapping)
            "sample_counts": sample_counts,
            "minimal_complete": minimal_ok,
            "fulsome_complete": fulsome_ok,
            "minimal_unmet": minimal_unmet,
            "fulsome_unmet": fulsome_unmet,
        }
