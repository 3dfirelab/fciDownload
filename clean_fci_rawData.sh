#!/bin/bash

# Set base directory
DATA_DIR="/mnt/data3/SILEX/MTG-FCI/data"

# Get yesterday's date in YYYYMMDD format
YESTERDAY=$(date -d "yesterday" +"%Y%m%d")

# Loop over directories
for dir in "$DATA_DIR"/*; do
    if [ -d "$dir" ]; then
        dirname=$(basename "$dir")
        # Check if directory name is a valid date and older than yesterday
        if [[ "$dirname" =~ ^[0-9]{8}$ ]] && [ "$dirname" -lt "$YESTERDAY" ]; then
            echo "Deleting directory: $dir"
            rm -rf "$dir"
        fi
    fi
done
