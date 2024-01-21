#!/bin/bash

# get the publish time of all versions
# use command `npm view "$package" time`

if ! command -v npm &> /dev/null
then
    echo "npm could not be found, please install npm."
    exit
fi

jsonFile="publishTimeAll.json"

echo "{}" > "$jsonFile"

while IFS= read -r package
do
    echo "Fetching release time for $package"
    publishTime=$(npm view "$package" time --json)
    if [ $? -eq 0 ]; then
        jq --arg pkg "$package" --argjson time "$publishTime" '.[$pkg]=$time' "$jsonFile" > temp.$$.json && mv temp.$$.json "$jsonFile"
    else
        echo "Error fetching release time for $package" >> error.log
    fi
done < "$1"


cat "$jsonFile"