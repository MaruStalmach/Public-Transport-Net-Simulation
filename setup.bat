@echo off

python -m venv venv

echo Activating the virtual environment...
call venv\Scripts\activate.bat

echo Installing requirements...
pip install -r requirements.txt

echo Installing project in editable mode...
pip install -e .