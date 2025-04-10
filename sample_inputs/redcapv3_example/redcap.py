import mappings
import re


def replace_stage_2(data_values):
    """There is currently an error in the data model where there is no, 'Stage 2', so we will temporarily replace it
    with 'Stage II' """
    val = mappings.single_val(data_values)
    if val == "Stage 2":
        return "Stage II"
    else:
        return val
