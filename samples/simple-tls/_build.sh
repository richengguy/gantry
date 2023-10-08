#!/bin/bash

function get_state() {
    docker compose ps --format json $1 | jq -r '.State'
}

gantry build compose -o $OUTPUT_FOLDER $SAMPLE_FOLDER

# Build the sample docker images and verify it can be brought up successfully.
cd $OUTPUT_FOLDER/simple-tls
docker compose build
docker compose up -d

echo "Sleeping for 1 second..."
sleep 1s

hello_world_state=`get_state hello-world`
proxy_state=`get_state proxy`

if [[ "$hello_world_state" == "running" && "$proxy_state" == "running" ]];
then
    exit_code=0
else
    exit_code=1
fi

docker compose down

exit $exit_code
