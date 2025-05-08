## Example of using clinical_etl_code to create genomic ingest json

These files will convert a csv mapping file with donor and sample information into the json required for ingest into CanDIG.

This example is using a batch of vcf files.

To run, from this directory:

```bash
python parse_genomic_mapping_file.py --mapping-csv file-location-sample-mapping.csv
CSVConvert --input tmp_out --manifest genomic_manifest.yml
```
