#!/bin/bash

export LOG_DIR=logs/
export LOG_LEVEL=DEBUG

uv run quart --debug run -h 127.0.0.1 -p 5000 --reload
