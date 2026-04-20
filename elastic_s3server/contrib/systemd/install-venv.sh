# Create the venv
python3 -m venv /opt/s3server/venv

# Install the required packages
/opt/s3server/venv/bin/pip install --upgrade pip
/opt/s3server/venv/bin/pip install -r /opt/s3server/server/requirements.txt