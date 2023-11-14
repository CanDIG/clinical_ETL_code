from lazydocs import MarkdownGenerator
import mappings


def main():
    generator = MarkdownGenerator()
    mappings_docs = generator.import2md(mappings)

    with open("mapping_functions.md", "r") as f:
        mapping_functions_lines = f.readlines()

    updated_mapping_functions = []
    for line in mapping_functions_lines:
        if line.startswith("## Standard Functions Index"):
            break
        else:
            updated_mapping_functions.append(line)
    updated_mapping_functions.append("## Standard Functions Index\n")
    updated_mapping_functions.append(mappings_docs)
    with open("mapping_functions.md", "w+") as f:
        f.writelines(updated_mapping_functions)


if __name__ == '__main__':
    main()
