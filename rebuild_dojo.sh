#!/bin/bash

# Stop and remove the existing container if it exists
echo "[+] Stopping and removing existing container..."
docker stop dojo 2>/dev/null
docker rm dojo 2>/dev/null

# Build the Docker image
echo "[+] Building the Docker image..."
docker build -t pwncollege/dojo .

# Run the container
echo "[+] Running the container..."
docker run \
    --name dojo \
    --privileged \
    -v "$(pwd):/opt/pwn.college" \
    -v "$(pwd)/data:/data" \
    -p 2222:22 -p 80:80 -p 443:443 \
    -d \
    pwncollege/dojo

# Show logs
echo "[+] Showing container logs..."
docker exec dojo dojo logs
