import json
from datetime import datetime

# Get the publish date of specific version of packages

with open('publishTime.json', 'r') as f:
    data = json.load(f)

filtered_data = {}
for package_version, times in data.items():
    package, version = package_version.rsplit('@', 1)
    if version in times:
        filtered_data[package_version] = {
            version: times[version]
        }

sorted_data = sorted(
    filtered_data.items(),
    key=lambda item: datetime.strptime(list(item[1].values())[0], "%Y-%m-%dT%H:%M:%S.%fZ")
)

sorted_data_old_to_new = {item[0]: item[1] for item in sorted_data}


with open('specificTime.json', 'w') as f:
    json.dump(filtered_data, f, indent=4)

with open('specificTime_sorted.json', 'w') as f:
    json.dump(sorted_data_old_to_new, f, indent=4)

print("finished.")