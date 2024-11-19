#!/usr/bin/env bash
# Updates the moh_template based on the schema.
# Manual differences are recorded in tests/moh_diffs.txt

python src/clinical_etl/generate_schema.py --out moh_template
diff moh_template.csv moh_v3_template.csv > curr_diff.txt
bytes=$(head -5 curr_diff.txt | wc -c)
dd if=curr_diff.txt  bs="$bytes" skip=1 conv=notrunc of=tests/moh_diffs1.txt
mv tests/moh_diffs1.txt tests/moh_diffs.txt
rm curr_diff.txt
