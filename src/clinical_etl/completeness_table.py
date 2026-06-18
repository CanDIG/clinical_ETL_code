import argparse
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=str, required=True, help="Path to input json file"
    )
    args = parser.parse_args()
    return args


def generate_csv(input_path):
    output_path = input_path.replace("_map.json", "_completeness.csv")
    print(f"Converting {input_path} to {output_path}")
    with open(input_path) as f:
        stats_dict = json.load(f)["statistics"]
        with open(output_path, "w") as out:
            out.write("Schema,Field,Total,Missing,Percent Missing\n")
            required_but_missing = stats_dict["required_but_missing"]
            for k, v in required_but_missing.items():
                for field, stats in v.items():
                    total = stats["total"]
                    missing = stats["missing"]
                    missing_percent = missing / total * 100
                    out.write(f"{k},{field},{total},{missing},{round(missing_percent)}\n")


def generate_donor_completeness_csv(input_path):
    """Write a per-donor tier/level completeness table from a
    *_validation_results.json file (which holds the donor-ID-keyed records)."""
    output_path = input_path.replace("_validation_results.json", "_donor_completeness.csv")
    print(f"Converting {input_path} to {output_path}")
    with open(input_path) as f:
        donors = json.load(f).get("donor_completeness", {})
    with open(output_path, "w") as out:
        out.write("Donor,Tier,Level,Type,Minimal Complete,Fulsome Complete,Unmet (fulsome)\n")
        for donor_id, rec in donors.items():
            out.write(
                f"{donor_id},{rec['tier'] or ''},{rec['level']},{rec['type']},"
                f"{rec['minimal_complete']},{rec['fulsome_complete']},"
                f"{'|'.join(rec['fulsome_unmet'])}\n"
            )


def main(input_path):
    """Dispatch on file type: aggregate field stats from a _map.json, or the
    per-donor tier/level table from a _validation_results.json."""
    with open(input_path) as f:
        data = json.load(f)
    if "donor_completeness" in data:
        generate_donor_completeness_csv(input_path)
    elif "statistics" in data:
        generate_csv(input_path)
    else:
        raise SystemExit(
            "Input json has neither 'statistics' (a _map.json) nor "
            "'donor_completeness' (a _validation_results.json)."
        )


if __name__ == "__main__":
    args = parse_args()
    main(args.input)
