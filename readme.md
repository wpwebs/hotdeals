### Create a Dev Container Project then open it in VSCode

_The development environment will install Jupyter Notebook and Oh My Zsh with plugins, theme with customize Zsh prompt_

### Usage: 
```sh
# Start project and open the code container in VSCode:
./start_devcontainer.sh [Project Name] [Environment]
"environment: development | dev | production | prod"

# Stopping the Services:
project_name=HotDeals
docker stop $project_name
```

**Example:**
```sh
# Build and Open the project container in VSCode - development environment 
./start_devcontainer.sh
./start_devcontainer.sh HotDeals development
./start_devcontainer.sh HotDeals dev

# Build and Open the project container in VSCode - development environment 
./start_devcontainer.sh HotDeals production
./start_devcontainer.sh HotDeals prod

```

```sh
# Project Directory Structure
project/
├── start_devcontainer.sh
├── .gitignore
├── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile
├── .dot_files/
│   └── .p10k.zsh
├── .ssh/
│   ├──  ssh_key
│   └── ssh_key.pub
└── src/
    ├── __init__.py
    ├── requirements.txt
    ├── main.py
    └── ... (other source files)

# Preparing ssh_key file
mkdir -p .ssh
op read "op://dev/id_henry/public key" > .ssh/ssh_key.pub && chmod 644 .ssh/ssh_key.pub
op read "op://dev/id_henry/private key" > .ssh/ssh_key && chmod 600 .ssh/ssh_key
```

### commands
```sh
# define project name
project=hotdeals
# build image
docker build -f .devcontainer/Dockerfile  -t $project-image .

# run docker
docker run -d --name $project -v $(pwd):/code $project-image


# debug
docker run --name $project $project-image
# remove docker
docker rm $project -f  

docker image list
docker image rm $project-image

docker run --name $project -it --entrypoint /bin/zsh $project-image

docker exec -it $project /bin/zsh

