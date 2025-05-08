## Example of using clinical_etl_code to create genomic ingest json

These files will convert a csv mapping file with donor and sample information into the json required for ingest into CanDIG.

This example is using a batch of vcf files.

To run, from this directory:

```bash
python parse_genomic_mapping_file.py --mapping-csv file-location-sample-mapping.csv
CSVConvert --input tmp_out --manifest genomic_manifest.yml
```

> [!IMPORTANT]  
> Currently, after conversion you need to strip things out of the json produced so that ingest can occur, the genomic ingest json needs to be just a list of the genomic json objects, so all other parts of the json should be deleted (we will work on fixing this)

i.e. the keys at the start of the file `openapi_url`, `schema_class` and `genomic_ids` keys should be deleted and the list inside the `genomic_ids` key is retained. The `statistics` object should also be deleted

e.g. of a valid genomic ingest json

```json
[
        {
            "program_id": "TEST_PROGRAM",
            "genomic_file_id": "SAMPLE_0007013-ST.mutect2.filtered.vep.PASS",
            "metadata": {
                "sequence_type": "wgs",
                "data_type": "variant",
                "reference": "hg38"
            },
            "main": {
                "name": "SAMPLE_0007013-ST.mutect2.filtered.vep.PASS.vcf.gz",
                "access_method": "https://your.ecs.endpoint.ca/your-s3-bucket/folder-in-bucket/SAMPLE_0007013-ST.mutect2.filtered.vep.PASS.vcf.gz"
            },
            "index": {
                "name": "SAMPLE_0007013-ST.mutect2.filtered.vep.PASS.vcf.gz.tbi",
                "access_method": "https://your.ecs.endpoint.ca/your-s3-bucket/folder-in-bucket/SAMPLE_0007013-ST.mutect2.filtered.vep.PASS.vcf.gz.tbi"
            },
            "samples": [
                {
                    "submitter_sample_id": "DONOR-00024-01-DT-01-D",
                    "genomic_file_sample_id": "SAMPLE_0007_013-ST"
                },
                {
                    "submitter_sample_id": "DONOR-00024-01-DN-01-D",
                    "genomic_file_sample_id": "SAMPLE_0007013-SB"
                }
            ]
        },
        {
            "program_id": "TEST_PROGRAM",
            "genomic_file_id": "SAMPLE_0014017-AT.mutect2.filtered.vep.PASS",
            "metadata": {
                "sequence_type": "wgs",
                "data_type": "variant",
                "reference": "hg38"
            },
            "main": {
                "name": "SAMPLE_0014017-AT.mutect2.filtered.vep.PASS.vcf.gz",
                "access_method": "https://your.ecs.endpoint.ca/your-s3-bucket/folder-in-bucket/SAMPLE_0014017-AT.mutect2.filtered.vep.PASS.vcf.gz"
            },
            "index": {
                "name": "SAMPLE_0014017-AT.mutect2.filtered.vep.PASS.vcf.gz.tbi",
                "access_method": "https://your.ecs.endpoint.ca/your-s3-bucket/folder-in-bucket/SAMPLE_0014017-AT.mutect2.filtered.vep.PASS.vcf.gz.tbi"
            },
            "samples": [
                {
                    "submitter_sample_id": "DONOR-00016-01-DN-01-D",
                    "genomic_file_sample_id": "SAMPLE_0014017-SB"
                },
                {
                    "submitter_sample_id": "DONOR-00016-01-DT-01-D",
                    "genomic_file_sample_id": "SAMPLE_0014_017-AT"
                }
            ]
        }, 
  ...
```