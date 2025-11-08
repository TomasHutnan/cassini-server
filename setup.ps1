# Create python virtual environment
python -m venv .venv

python -m pip install --upgrade pip

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install requirements
pip install --requirement requirements.txt