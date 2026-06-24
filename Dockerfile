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

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the app
# Use --server.enableCORS=false to avoid potential cross-origin issues
# Use --server.runOnSave=false for production
CMD ["streamlit", "run", "app.py", "--server.enableCORS=false", "--server.runOnSave=false"]
