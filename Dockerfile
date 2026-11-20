FROM python:3.11

# Set the working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# CTA downloads persist in the same mounted data directory as the database.
ENV ITR_CTA_PATH=/app/data/cta/current-Companies-Taking-Action.xlsx

# Supplied by the release workflow; local builds default to development.
ARG APP_VERSION=development
ENV ITR_APP_VERSION=${APP_VERSION}

# Enable the dataset database for this image's intended local use.
# This does not provide authentication or isolate users.
ENV ITR_DEPLOYMENT=local

# Expose the port Streamlit runs on.
EXPOSE 8501

# Listen on all interfaces inside the container so Docker can reach Streamlit.
# Restrict host access with the Compose mapping "127.0.0.1:8501:8501".
# Command-line options override .streamlit/config.toml.
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.runOnSave=false"]
