#!/bin/bash

python3 -m venv venv

echo "activating the virtual environment..."
source venv/bin/activate

echo "installing requirements..."
pip install -r requirements.txt

echo "installing project in editable mode..."
pip install -e .