#!/bin/env bash

# Check if a file was provided
if [ -z "$1" ]; then
    echo "Usage: ./run.sh path/to/file.cpp"
    exit 1
fi

file=$1
shift # Remove the first argument so $@ contains only the arguments for the executable

target_name=$(echo "$file" | sed 's/\.cpp$//' | sed 's/\//_/g')

cmake -S . -B build -G Ninja -Wno-dev > /dev/null 2>build_error.log

if [ $? -ne 0 ]; then
    echo "CMake Configuration failed. Check build_error.log"
    exit 1
fi

cmake --build build --target "$target_name"

if [ $? -eq 0 ]; then
    echo "--- Executing: $target_name ---"
    echo "--- Arguments: $@ ---"
    echo -e "-------------------------------\n"
    ./build/"$target_name" "$@"
    echo -e "\n--- Execution End ---\n"
else
    echo "Build failed."
    cat build_error.log
    exit 1
fi
