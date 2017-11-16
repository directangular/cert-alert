#!/bin/bash

docker build . -t directangular/cert-alert
if [[ $1 = push ]]; then
    docker push directangular/cert-alert
fi
