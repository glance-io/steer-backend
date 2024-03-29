# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container to /app
WORKDIR /app

COPY requirements.txt requirements.txt
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
