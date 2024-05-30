#!/bin/bash

VENV_DIR="venv"

# create virtual environment if it doesn't already exist
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment $VENV_DIR already exists. Skipping creation."
else
    python3 -m venv $VENV_DIR
    echo "Virtual environment $VENV_DIR created."
fi

# activate the virtual environment
source $VENV_DIR/bin/activate

# upgrade pip
pip install --upgrade pip

# install pip requirements individually to handle failures
while read package; do
    pip install "$package" || echo "Failed to install $package, skipping..."
done < requirements.txt

echo "Setup complete. To activate the virtual environment, run 'source $VENV_DIR/bin/activate'."
