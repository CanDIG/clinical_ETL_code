import mappings


def main():
    nivolumab_id = mappings.lookup_drug_identifier("nivolumab", "NCI Thesaurus")
    print("helloo")


if __name__ == "__main__":
    main()