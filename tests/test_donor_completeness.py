"""Tests for per-donor tier/level completeness (BaseSchema completeness engine).

Offline by design: MoHSchemaV3.__init__ fetches the OpenAPI schema over the
network, but the completeness engine only needs the class-level criteria and
the validation pass. We instantiate via __new__ and supply a permissive
json_schema ({} validates anything) so validate_ingest_map runs without network.

'fulsome' completeness is derived from the validation pass, so these tests run
the donor(s) through schema.validate_ingest_map and read the resulting
statistics["donor_completeness"], rather than calling the engine in isolation.
"""

import pytest

from clinical_etl.mohschemav3 import MoHSchemaV3
from clinical_etl.CSVConvert import summarize_completeness, build_completeness_failures


@pytest.fixture
def schema():
    s = MoHSchemaV3.__new__(MoHSchemaV3)          # bypass network __init__
    s.validation_warnings = []
    s.validation_errors = []
    s.statistics = {}
    s.identifiers = {}
    s.stack_location = []
    s.json_schema = {}                            # permissive: no jsonschema errors
    return s


def evaluate(schema, *donors):
    """Run donors through the full validation pass and return the per-donor
    completeness records keyed by donor id."""
    schema.validate_ingest_map({"donors": list(donors)})
    return schema.statistics["donor_completeness"]


# --- fixture builders ------------------------------------------------------ #

def sample(tn, stype, sid):
    return {
        "submitter_sample_id": sid,
        "tumour_normal_designation": tn,
        "specimen_tissue_source": "Blood derived",
        "specimen_type": "Primary tumour",
        "sample_type": stype,
    }


def tumour_dna(sid="S_TDNA"):
    return sample("Tumour", "Total DNA", sid)


def tumour_rna(sid="S_TRNA"):
    return sample("Tumour", "Total RNA", sid)


def normal_dna(sid="S_NDNA"):
    return sample("Normal", "Total DNA", sid)


def treatment():
    # treatment_type that does not require nested therapy/radiation/surgery objects
    return {
        "submitter_treatment_id": "TR1",
        "treatment_type": ["Bone marrow transplant"],
        "is_primary_treatment": "Yes",
        "treatment_start_date": {"month_interval": 0},
        "treatment_end_date": {"month_interval": 1},
        "treatment_intent": "Curative",
    }


def build_donor(donor_id="DONOR", samples=None, deceased="No",
                with_specimen_storage=True, with_staging=True,
                with_tumour_specimen_fields=True, with_treatment=True):
    """Build a donor that is fully (fulsome) complete by default; flip a knob
    to introduce a specific gap."""
    if samples is None:
        samples = [tumour_dna(), tumour_rna(), normal_dna()]
    specimen = {
        "submitter_specimen_id": "SP1",
        "specimen_collection_date": {"month_interval": 0},
        "specimen_anatomic_location": "C50",
        "sample_registrations": samples,
    }
    if with_specimen_storage:
        specimen["specimen_storage"] = "Frozen in liquid nitrogen"
    if with_tumour_specimen_fields:
        specimen.update({
            "reference_pathology_confirmed_diagnosis": "Yes",
            "reference_pathology_confirmed_tumour_presence": "Yes",
            "tumour_grading_system": "Two-tier grading system",
            "tumour_grade": "Low grade",
            "percent_tumour_cells_range": "51-100%",
            "percent_tumour_cells_measurement_method": "Image analysis",
        })
    primary_diagnosis = {
        "submitter_primary_diagnosis_id": "PD1",
        "date_of_diagnosis": {"month_interval": 0},
        "cancer_type_code": "C50.1",
        "primary_site": "Breast",
        "basis_of_diagnosis": "Histology of primary tumour",
        "specimens": [specimen],
    }
    if with_treatment:
        primary_diagnosis["treatments"] = [treatment()]
    if with_staging:
        primary_diagnosis["clinical_tumour_staging_system"] = "Revised International staging system (R-ISS)"
        primary_diagnosis["clinical_stage_group"] = "Stage I"
    return {
        "submitter_donor_id": donor_id,
        "gender": "Woman",
        "sex_at_birth": "Female",
        "date_of_birth": {"month_interval": 0},
        "date_resolution": "month",
        "is_deceased": deceased,
        "program_id": "PROGRAM_1",
        "primary_diagnoses": [primary_diagnosis],
    }


# --- _field_present: "Not available" counts as complete -------------------- #

def test_not_available_is_a_valid_value(schema):
    assert schema._field_present({"x": "Not available"}, "x") is True
    assert schema._field_present({"x": "Woman"}, "x") is True
    assert schema._field_present({"x": ""}, "x") is False
    assert schema._field_present({"x": None}, "x") is False
    assert schema._field_present({}, "x") is False


# --- tier classification (exclusive) --------------------------------------- #

def test_tier_a(schema):
    rec = evaluate(schema, build_donor())["DONOR"]
    assert rec["tier"] == "A"
    assert rec["sample_counts"] == {"tumour_dna": 1, "tumour_rna": 1, "normal_dna": 1}
    assert rec["tier_criteria_met"] == {"A": True, "B": True}  # diagnostic overlap only


def test_tier_b(schema):
    rec = evaluate(schema, build_donor(samples=[tumour_dna(), normal_dna()]))["DONOR"]
    assert rec["tier"] == "B"
    assert rec["tier_criteria_met"] == {"A": False, "B": True}


def test_tier_none_when_composition_incomplete(schema):
    rec = evaluate(schema, build_donor(samples=[tumour_dna()]))["DONOR"]
    assert rec["tier"] is None


def test_summary_buckets(schema):
    recs = evaluate(
        schema,
        # Tier A, fulsome
        build_donor(donor_id="DONOR_AF"),
        # Tier B, fulsome
        build_donor(donor_id="DONOR_BF", samples=[tumour_dna(), normal_dna()]),
        # Tier A, minimal only (missing conditional staging -> not fulsome)
        build_donor(donor_id="DONOR_AM", with_staging=False),
        # No qualifying tier (single tumour DNA sample)
        build_donor(donor_id="DONOR_N", samples=[tumour_dna()]),
    )
    summary = summarize_completeness(recs)
    assert summary["total_donors"] == 4
    # minimal partition (sums to 4); Tier A donor never counted toward Tier B
    assert summary["tier_a_min_clinical_complete"] == 2   # AF, AM
    assert summary["tier_b_min_clinical_complete"] == 1   # BF
    assert summary["incomplete_min_donors"] == 1          # N
    # fulsome partition (sums to 4)
    assert summary["tier_a_full_clinical_complete"] == 1  # AF
    assert summary["tier_b_full_clinical_complete"] == 1  # BF
    assert summary["incomplete_full_donors"] == 2         # AM (minimal only), N


# --- fulsome vs minimal ---------------------------------------------------- #

def test_fully_complete_donor_is_fulsome(schema):
    rec = evaluate(schema, build_donor())["DONOR"]
    assert rec["fulsome_unmet"] == []
    assert rec["fulsome_complete"] is True
    assert rec["minimal_complete"] is True
    assert rec["level"] == "fulsome"
    assert rec["type"] == "Tier A fulsome"


def test_missing_flat_required_breaks_fulsome(schema):
    # specimen_storage is required but is not part of the minimal set
    rec = evaluate(schema, build_donor(with_specimen_storage=False))["DONOR"]
    assert rec["minimal_complete"] is True
    assert rec["fulsome_complete"] is False
    assert rec["level"] == "minimal"
    assert any("specimen_storage" in u for u in rec["fulsome_unmet"])


def test_missing_treatment_breaks_fulsome(schema):
    # every donor must have >= 1 treatment object (required_instances)
    rec = evaluate(schema, build_donor(with_treatment=False))["DONOR"]
    assert rec["fulsome_complete"] is False
    assert any("treatments" in u for u in rec["fulsome_unmet"])
    assert rec["minimal_complete"] is True   # treatment existence is not a minimal criterion


def test_missing_staging_is_a_conditional_gap(schema):
    # conditional requirement raised in validate_primary_diagnoses
    rec = evaluate(schema, build_donor(with_staging=False))["DONOR"]
    assert rec["fulsome_complete"] is False
    assert any("clinical_tumour_staging_system" in u or "staging" in u
               for u in rec["fulsome_unmet"])
    assert rec["minimal_complete"] is True   # staging not in the minimal set


def test_missing_tumour_specimen_fields_is_a_conditional_gap(schema):
    # conditional requirement raised in validate_specimens for Tumour samples
    rec = evaluate(schema, build_donor(with_tumour_specimen_fields=False))["DONOR"]
    assert rec["fulsome_complete"] is False
    assert any("Tumour specimens require" in u for u in rec["fulsome_unmet"])
    assert rec["minimal_complete"] is True


def test_deceased_without_death_fields_is_a_conditional_gap(schema):
    rec = evaluate(schema, build_donor(deceased="Yes"))["DONOR"]
    assert rec["fulsome_complete"] is False
    assert any("cause_of_death" in u for u in rec["fulsome_unmet"])
    assert any("date_of_death" in u for u in rec["fulsome_unmet"])
    assert rec["minimal_complete"] is True   # death fields not in the minimal set


# --- "Not available" rule flows through fulsome ---------------------------- #

def test_not_available_keeps_donor_fulsome(schema):
    donor = build_donor()
    donor["gender"] = "Not available"
    rec = evaluate(schema, donor)["DONOR"]
    assert rec["fulsome_complete"] is True


def test_blank_value_breaks_fulsome(schema):
    donor = build_donor()
    donor["gender"] = ""
    rec = evaluate(schema, donor)["DONOR"]
    assert rec["fulsome_complete"] is False
    assert any(u.endswith(".gender") for u in rec["fulsome_unmet"])


# --- detailed failure report ----------------------------------------------- #

def test_completeness_failures_report(schema):
    recs = evaluate(
        schema,
        build_donor(donor_id="DONOR_AF"),                       # fully complete
        build_donor(donor_id="DONOR_AM", with_staging=False),   # tier A, not fulsome
        build_donor(donor_id="DONOR_N", samples=[tumour_dna()]),  # untiered
    )
    report = build_completeness_failures(recs, schema.tier_criteria)

    assert report["total_donors"] == 3
    assert report["failing_donors"] == 2
    ids = {d["donor_id"] for d in report["donors"]}
    assert "DONOR_AF" not in ids          # fully complete -> excluded
    assert ids == {"DONOR_AM", "DONOR_N"}

    am = next(d for d in report["donors"] if d["donor_id"] == "DONOR_AM")
    assert am["fulsome_complete"] is False
    assert any("fulsome" in r.lower() for r in am["reasons"])
    assert any("staging" in u.lower() for u in am["fulsome_unmet"])

    n = next(d for d in report["donors"] if d["donor_id"] == "DONOR_N")
    assert n["tier"] is None
    assert any("Sample composition" in r for r in n["reasons"])
