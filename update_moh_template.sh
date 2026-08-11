#!/usr/bin/env bash
# Updates the moh_template based on the schema.
# Manual differences are recorded in tests/moh_diffs.txt

python src/clinical_etl/generate_schema.py --out moh_template --url https://raw.githubusercontent.com/CanDIG/katsu/refs/heads/features/model_4/chord_metadata_service/mohpackets/docs/schemas/schema.json --schema MoHSchemaV4
diff moh_template.csv moh_v4_template.csv > curr_diff.txt
bytes=$(head -5 curr_diff.txt | wc -c)
dd if=curr_diff.txt  bs="$bytes" skip=1 conv=notrunc of=tests/moh_diffs1.txt
mv tests/moh_diffs1.txt tests/moh_diffs.txt
rm curr_diff.txt
