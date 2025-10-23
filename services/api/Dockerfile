# Stage 1: Build the application with dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Copy the necessary files for installing the project
COPY pyproject.toml .
COPY src ./src
COPY services/api/requirements.txt .

# Install the project and its dependencies into a virtual environment
# The '-e .' in requirements.txt will now work because pyproject.toml is present
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual API server code
COPY services/api/main.py .


# Stage 2: Create the final, lean production image
FROM python:3.11-slim

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code that needs to be run
COPY --from=builder /app/main.py .
COPY --from=builder /app/src ./src

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8080

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]