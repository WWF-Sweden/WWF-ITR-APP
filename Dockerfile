FROM python:3.11

# Set the working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the SBTi CTA file so the app works without network at runtime.
# The file is cached inside the image; USE_LOCAL_CTA=True in scoring.py ensures
# no download is attempted when containers start.
RUN python -c "from ITR.data.sbti import SBTi; SBTi()" \
    || echo "Warning: CTA file could not be pre-downloaded (no network at build time)"

# Copy the rest of the application code
COPY . .

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the app
# Use --server.enableCORS=false to avoid potential cross-origin issues
# Use --server.runOnSave=false for production
CMD ["streamlit", "run", "app.py", "--server.enableCORS=false", "--server.runOnSave=false"]
