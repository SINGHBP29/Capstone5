# Use a specific Python version for reproducibility
FROM python:3.11-slim as builder

# Set the working directory
WORKDIR /app

# Copy only the requirements file to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# --- Final Stage ---
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app .

# Set the entrypoint to run the catalog agent by default
# This can be overridden when running the container
ENTRYPOINT ["python3", "-m", "Catalog.RootCause.google_agent"]
