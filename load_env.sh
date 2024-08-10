#!/bin/bash

log_and_export_env() {
    while IFS= read -r line; do
        if [[ "$line" =~ ^#.* ]] || [[ -z "$line" ]]; then
            echo "Skipped comment/empty line: '$line'"
            continue
        fi
        if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*=.* ]]; then
            echo "Exporting: '$line'"
            export "$line"
        else
            echo "Skipped invalid line: '$line' (reason: not in 'KEY=VALUE' format)"
        fi
    done < /home/plato/dev/ella-ai/.env
}