# get common & different dependencies
def find_common_lines(file1_path, file2_path, result_file):
    with open(file1_path, 'r', encoding='utf-8') as f1:
        file1_lines = {line.strip() for line in f1}

    with open(file2_path, 'r', encoding='utf-8') as f2:
        file2_lines = {line.strip() for line in f2}

    common_lines = file1_lines.intersection(file2_lines)
    num_common_lines = len(common_lines)

    with open(result_file, 'w', encoding='utf-8') as output:
        if common_lines:
            output.write("\n\nExist in Both files:\n")
            for line in common_lines:
                output.write(line + "\n")

        in_file1_not_in_file2 = file1_lines - file2_lines
        in_file2_not_in_file1 = file2_lines - file1_lines
        num_only_file1 = len(in_file1_not_in_file2)
        num_only_file2 = len(in_file2_not_in_file1)

        if in_file1_not_in_file2 or in_file2_not_in_file1:
            if in_file1_not_in_file2:
                output.write(f"\n\nOnly exist in {file1_path} :\n")
                for line in in_file1_not_in_file2:
                    output.write(line + "\n")
            if in_file2_not_in_file1:
                output.write(f"\n\nOnly exist in {file2_path} :\n")
                for line in in_file2_not_in_file1:
                    output.write(line + "\n")

        output.write(f'\ncommon deps: {num_common_lines}\n')
        output.write(f'deps only in {file1_path}: {num_only_file1}\n')
        output.write(f'deps only in {file2_path}: {num_only_file2}\n')

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 4:
        print("usage: python compare_texts_to_file.py file1_path file2_path result_file")
        sys.exit(1)

    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    result_file = sys.argv[3]
    find_common_lines(file1_path, file2_path, result_file)
