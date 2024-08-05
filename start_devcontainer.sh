#!/bin/bash

# Define the project name
project_name=${1:-HotDeals}

# Function to print usage
print_usage() {
  echo "Usage: $0 [Project Name] [Environment]"
  echo "environment: development | dev | production | prod"
  exit 1
}

# Prepare ssh_key
cp $HOME/.ssh/ssh_key* .dot_files

# Define the project name and image tag
# Convert to lowercase
project=$(echo "$project_name" | tr '[:upper:]' '[:lower:]')
# Replace spaces with underscores
project="${project// /_}"

workspace_folder="/code"

# Set default environment if not provided
environment=${2:-development}
target=$environment

# Validate the environment argument
if [[ "$environment" != "development" && "$environment" != "dev" && "$environment" != "production" && "$environment" != "prod" ]]; then
  echo "Error: Invalid environment '$environment'."
  print_usage
fi

if [[ "$environment" == "dev" ]] || [[ "$environment" == "development" ]]; then
  target=development
  image_tag="$project-dev-image"
fi

if [[ "$environment" == "prod" ]] || [[ "$environment" == "production" ]]; then
  target=production
  image_tag="$project-prod-image"
fi

# Use sed command searches for the "name" key and replaces its value with the project_name
sed -i.bak -E "s/\"name\": \"[^\"]+\"/\"name\": \"$project_name\"/" .devcontainer/devcontainer.json
rm .devcontainer/devcontainer.json.bak

# Define the Dockerfile and context directory
dockerfile_path=".devcontainer/Dockerfile"
context_dir="."

# Function to compute the hash of the Dockerfile and context directory
compute_hash() {
  find "$dockerfile_path" "$context_dir" -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}'
}

# Compute the current hash
current_hash=$(compute_hash)

# Check if a hash file exists and read the previous hash
hash_file=".dot_files/.docker_build_hash"
if [ -f "$hash_file" ]; then
  previous_hash=$(cat "$hash_file")
else
  previous_hash=""
fi

# Function to build the Docker image
build_image() {
  echo "Building Docker image for the project..."
  docker build --build-arg ENVIRONMENT=$environment --target $target -f "$dockerfile_path" -t "$image_tag" "$context_dir"
  if [ $? -ne 0 ]; then
    echo "Docker image build failed."
    exit 1
  fi
  # Save the current hash to the hash file
  echo "$current_hash" > "$hash_file"
}

# Check if the image needs to be rebuilt
if [ "$current_hash" != "$previous_hash" ]; then
  build_image
else
  echo "Docker image is up to date. No build necessary."
fi

# Check if a container with the same name is already running
existing_container=$(docker ps -aq -f name=$project)
if [ -n "$existing_container" ]; then
  echo "A container with the name $project already exists. Removing the existing container..."
  docker rm -f $existing_container
  if [ $? -ne 0 ]; then
    echo "Failed to remove the existing container."
    exit 1
  fi
fi

# Run the Docker container
echo "Running Docker container..."
docker run -d --name $project -v $(pwd):$workspace_folder $image_tag
if [ $? -ne 0 ]; then
  echo "Failed to start the Docker container."
  exit 1
fi

# Clean up dangling images and stopped containers
echo "Cleaning up unused Docker resources..."
docker image prune -f

# Retrieve the container ID
HEX_CONFIG=$(printf {\"containerName\":\"/$project\"} | od -A n -t x1 | tr -d '[\n\t ]')
if [ -z "$HEX_CONFIG" ]; then
    echo "Failed to retrieve the container ID."
    exit 1
fi

echo "Docker container is running with ID $HEX_CONFIG. Attaching to VS Code..."

# Attach to the running container using VS Code
code --folder-uri "vscode-remote://attached-container+$HEX_CONFIG$workspace_folder"
if [ $? -ne 0 ]; then
    echo "Failed to attach VS Code to the container."
    exit 1
fi

echo "Attached to VS Code successfully."