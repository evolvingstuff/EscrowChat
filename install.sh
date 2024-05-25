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

# install pip requirements
pip install --upgrade pip
pip install -r requirements.txt
echo "Setup complete. To activate the virtual environment, run 'source $VENV_DIR/bin/activate'."
