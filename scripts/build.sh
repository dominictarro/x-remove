#!/bin/bash
####################################################################################################
#
# Builds and pushes the Docker image to Amazon ECR.
#
# Usage: ./build.sh <tag> [profile] [-h|--help]

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
    echo "Usage: $0 <tag> [profile] [-h|--help]"
    echo
    echo "Builds and pushes the Docker image to Amazon ECR."
    echo
    echo "Arguments:"
    echo "    tag: the tag to apply to the Docker image"
    echo "    profile: the AWS profile to use (default: default)"
    echo
    echo "Example:"
    echo "    $0 0.0.1-beta.1"
}

tag=$1

if [ -z $tag ] || [ `is_help $@` == true ]; then
  show_help
  exit 1
fi

profile=$2

if [ -z $profile ]; then
  profile=default
fi

AWS_REGION=`aws configure get region --profile $profile`
AWS_ACCOUNT_ID=`aws sts get-caller-identity --query Account --output text --profile $profile`

echo Logging in to Amazon ECR...
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com && \
  echo Building the Docker image... && \
  fulltag=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/x-remove-server:$tag && \
  docker build . -t $fulltag --platform linux/amd64 && \
  echo Pushing the Docker image... && \
  docker push $fulltag
