#!/bin/bash

# Directly specify the full path to avoid issues with tilde expansion
SEARCH_DIR="/home/plato/dev/ella-ai/ella/lib64/python3.11/site-packages/memgpt"

# Echo the directory path to verify it's correct (optional, for debugging)
echo "Searching in directory: $SEARCH_DIR"

# Find files with SQLite likely extensions recursively
find "$SEARCH_DIR" -type f \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \)
