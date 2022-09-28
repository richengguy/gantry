#!/bin/bash

gantry build-compose -s $SAMPLE_FOLDER -o $OUTPUT_FOLDER

# Build the sample docker images
cd $OUTPUT_FOLDER
docker compose build
