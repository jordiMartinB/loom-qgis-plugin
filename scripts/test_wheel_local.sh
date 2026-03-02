#!/bin/bash
set -e

# Set up the environment
echo "Setting up the environment..."
# Add any environment setup commands here

# Run the tests
echo "Running tests..."
python3 -m unittest discover -s tests -p "*.py"