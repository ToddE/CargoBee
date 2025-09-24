# Use an official, slim Python image as a starting point
FROM python:3.12-slim-bullseye

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's caching
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Tell Fly.io what port your application will listen on
EXPOSE 8080

# The command to run your Gunicorn server when the container starts
# Binds the server to all network interfaces on the port Fly.io expects
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
