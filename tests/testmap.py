import clinical_etl.mappings

def indexed_on_if_absent(data_values):
    #{'submitter_donor_id': {'Followup': ['DONOR_1', 'DONOR_1', 'DONOR_1', 'DONOR_1']}, 'submitter_primary_diagnosis_id': {'Followup': ['PD_1', None, None, None]}, 'submitter_treatment_id': {'Followup': [None, 'TR_1', None, None]}}
    # [None, None, 'DONOR_1', 'DONOR_1']

    # [None, None, None, None] + ['DONOR_1', 'DONOR_1', 'DONOR_1', 'DONOR_1']
    # ['DONOR_1', 'DONOR_1', 'DONOR_1', 'DONOR_1'] + ['PD_1', None, None, None]
    # [None, 'DONOR_1', 'DONOR_1', 'DONOR_1'] + [None, 'TR_1', None, None]
    # [None, None, 'DONOR_1', 'DONOR_1']
    # {'submitter_donor_id': {'Followup': 'DONOR_1'}, 'submitter_primary_diagnosis_id': {'Followup': 'PD_1'}, 'submitter_treatment_id': {'Followup': None}}
    result = []

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
        "field": "submitter_donor_id",
        "sheet": "Followup",
        "values": result
    }

def fake_map(data_values):
    """Return a dict with a placeholder key."""
    return "test string"
