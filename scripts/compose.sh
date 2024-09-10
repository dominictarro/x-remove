#!/bin/bash
####################################################################################################
#
# Composes the x-remove web server using Docker Compose

function is_help() {
    for arg in $@; do
        if [ $arg == "-h" ] || [ $arg == "--help" ]; then
            echo true
            return 0
        fi
    done
    echo false
}

function show_help() {
    echo
    echo "Usage: $0 [-h|--help] <image> [host_data_mount]"
    echo
    echo "Composes the x-remove-server web server using Docker Compose"
    echo
    echo "Arguments:"
    echo "    image: the Docker image tag to use"
    echo "    host_data_mount: the host directory to mount as /data in the container. Default: /mnt/data"
    echo
    echo "Example:"
    echo "    $0 x-remove-server:0.0.1-beta.1"
}

if [ `is_help $@` == true ] || [ -z $1 ]; then
  show_help
  exit 1
fi

if [ -z $2 ]; then
  export HOST_DATA=/mnt/data
else
  export HOST_DATA=$2
fi
export IMAGE_NAME=${1%:*}
export IMAGE_TAG=${1##*:}

# Run Docker Compose with the specified image name
docker compose up -d
