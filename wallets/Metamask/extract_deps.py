import sys
import os

file_path = sys.argv[1]
base_name, extension = os.path.splitext(file_path)
# file_path = '11.4.1_extension.txt'
output_file_1 = f"{base_name}_deps_list_gav{extension}"
output_file_2 = f"{base_name}_deps_list{extension}"
output_file_3 = f"{base_name}_deps_list_gav_without_npm{extension}"
output_file_4 = f"{base_name}_other_lines{extension}"  


dependencies = []
dependencies_without_v = []
dependencies_gav_without_npm =[]
other_lines = []

skip_until_pipe = False

with open(file_path, 'r') as file:
    # for line in file:
    #     with open(file_path, 'r') as file:
    for line in file:

        if "Exported Binaries" in line or "Dependencies" in line:
            skip_until_pipe = True
            continue

        if skip_until_pipe:
            if line.strip() in ('│  │', '│'):
                skip_until_pipe = False
            continue

        if any(keyword in line for keyword in ["Instance", "Version"]):
            continue 

        if line.strip().startswith('└─ ') or line.strip().startswith('├─ '):
        
            dep_name = " ".join(line.strip().split()[1:])

            if '@' in dep_name:
                dep_name_without_v = dep_name.rsplit('@', 1)[0]
                dep_name_gav_without_npm = dep_name.replace("@npm:", "@")

            dependencies.append(dep_name)
            dependencies_without_v.append(dep_name_without_v)
            dependencies_gav_without_npm.append(dep_name_gav_without_npm)

        else:
            other_lines.append(line)



def write_to_file(filename, data):
    with open(filename, 'w') as file:
        
        for dep in sorted(set(data)):  
            file.write(dep + '\n')
        file.write(f"Total lines: {len(set(data))}\n\n")  

write_to_file(output_file_1, dependencies)
write_to_file(output_file_2, dependencies_without_v)
if sorted(set(dependencies)) != sorted(set(dependencies_gav_without_npm)):
    write_to_file(output_file_3, dependencies_gav_without_npm)

write_to_file(output_file_4, other_lines)

print(f"All unique dependency names have been saved to {output_file_1}, {output_file_2}, and {output_file_3}")
print(f"All other lines have been saved to {output_file_4}")