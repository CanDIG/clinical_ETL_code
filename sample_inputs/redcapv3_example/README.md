## v3 REDcap->v3 MoHCCN Clinical Data model


## `preprocess_redcap_data.py`
Some caveats:
- assumes you have two outputs for a redcap export, one raw and one called 'LABELS'
- Some preprocessing steps may be very specific to the PM2C way of modelling the data, e.g.
  - dates containing `Unk` (see `fix_dates` method)
    - Replaces 'Unk' in the 'day' value of a date with 15 as per data curation guidelines
    - If 'month' is `Unk`, returns a None value 
  - Censors dates if they don't make sense (see method `remove_problem_dates`)
    - uses an output file from validation during CSVConvert remove some dates if they don't make sense. The method here may not suit everyone's preferred logic for dealing with dates that don't make sense
  - Performs censoring of drug names (see `censor_drug_names` method)
    - Replaces any drug names in `systemic_therapy.drug_name` with `Investigational agent` if it does not appear in the `drug_allow_list`
  - Assumes that all specific treatment types linked to a treatment are nested as numbered columns within the treatment table (see lines 239-521 and `melt_dataframe` method)
  - Assumes a specific naming for identifiers based on their source schema (see lines 206-222)