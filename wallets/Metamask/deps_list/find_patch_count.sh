#!/bin/bash

# Text file path to read from
FILE="$1"

# Use `grep` to exclude lines containing "@npm:" or "@patch:"
grep -c -i -e "@patch:" "$FILE" 
grep "@patch:" "$FILE" > patch_list.txt

