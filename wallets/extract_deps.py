import sys
import os

file_path = sys.argv[1]
base_name, extension = os.path.splitext(file_path)
# file_path = '11.4.1_R_extension.txt'
output_file_1 = f"{base_name}_deps_list_gav{extension}"
output_file_2 = f"{base_name}_deps_list{extension}"
output_file_3 = f"{base_name}_deps_list_gav_without_npm{extension}"

# output_file = '11.4.1_dependencies_list.txt'

dependencies = []
dependencies_without_v = []
dependencies_gav_without_npm =[]

with open(file_path, 'r') as file:
    for line in file:
        if line.strip().startswith('└─ ') or line.strip().startswith('├─ '):
            dep_name = " ".join(line.strip().split()[1:])
            if '@' in dep_name:
                
                dep_name = dep_name
                dep_name_without_v = dep_name.rsplit('@', 1)[0]
                dep_name_gav_without_npm = dep_name.replace("@npm:", "@")
            dependencies.append(dep_name)
            dependencies_without_v.append(dep_name_without_v)
            dependencies_gav_without_npm.append(dep_name_gav_without_npm)




with open(output_file_1, 'w') as file:
    for dep in sorted(set(dependencies)):  
        file.write(dep + '\n')

with open(output_file_2, 'w') as file:
    for dep in sorted(set(dependencies_without_v)):  
        file.write(dep + '\n')

if sorted(set(dependencies)) != sorted(set(dependencies_gav_without_npm)):
    with open(output_file_3, 'w') as file:
        for dep in sorted(set(dependencies_gav_without_npm)):  
            file.write(dep + '\n')

            print(f'Generated deps without npm {output_file_3}')


print(f"All unique dependency names have been saved to {output_file_1} & {output_file_2}")