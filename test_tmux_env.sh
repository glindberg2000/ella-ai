#!/bin/bash

# Function to log and export valid environment variables
log_and_export_env() {
    while IFS= read -r line; do
        # Check if the line is a comment or empty
        if [[ "$line" =~ ^#.* ]] || [[ -z "$line" ]]; then
            echo "Skipped comment/empty line: '$line'"
            continue
        fi

        # Check if the line is a valid KEY=VALUE format
        if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*=.* ]]; then
            echo "Exporting: '$line'"
            export "$line"
        else
            echo "Skipped invalid line: '$line' (reason: not in 'KEY=VALUE' format)"
        fi
    done < /home/plato/dev/ella-ai/.env
}

# Run the function and display the exported environment variables
log_and_export_env

# Display the exported environment variables
echo "The following environment variables have been set:"
printenv | grep -E '^[A-Za-z_][A-Za-z0-9_]*='