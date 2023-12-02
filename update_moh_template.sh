#!/usr/bin/env bash


python generate_schema.py --url https://raw.githubusercontent.com/CanDIG/katsu/sonchau/uuid_with_fk/chord_metadata_service/mohpackets/docs/schema.yml --out tmp_template
diff tmp_template.csv moh_template.csv > test_data/moh_diffs.txt
bytes=$(head -5 test_data/moh_diffs.txt | wc -c)
dd if=test_data/moh_diffs.txt  bs="$bytes" skip=1 conv=notrunc of=test_data/moh_diffs.txt
rm tmp_template.csv
