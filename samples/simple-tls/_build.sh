#!/bin/bash

gantry build-compose -s $SAMPLE_FOLDER -o $OUTPUT_FOLDER

# Generate a self-signed cert
openssl req \
    -x509 -nodes \
    -newkey rsa:4096 \
    -keyout $OUTPUT_FOLDER/configuration/key.pem \
    -out $OUTPUT_FOLDER/configuration/cert.pem \
    -sha256 \
    -days 7

# Build the sample docker images
cd $OUTPUT_FOLDER
docker compose build
