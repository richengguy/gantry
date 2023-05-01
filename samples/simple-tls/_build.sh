#!/bin/bash

gantry build-compose -s $SAMPLE_FOLDER -o $OUTPUT_FOLDER

# Build the sample docker images and ensure all dependencies can be pulled down.
cd $OUTPUT_FOLDER
docker compose pull
docker compose build
