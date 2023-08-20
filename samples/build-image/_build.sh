#!/bin/bash
set -e

gantry build -o $OUTPUT_FOLDER -t example image $SAMPLE_FOLDER

docker_output=`docker run simple-app:example`

echo "Docker Output: ${docker_output}"

if [[ "$docker_output" != "Hello, world!" ]]; then
    exit 1
fi
