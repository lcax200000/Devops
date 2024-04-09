#!/bin/bash

docker pull thingsboard/tb-node:3.5.1
docker pull thingsboard/tb-web-ui:3.5.1
docker pull thingsboard/tb-js-executor:3.5.1
docker pull thingsboard/tb-http-transport:3.5.1
docker pull thingsboard/tb-mqtt-transport:3.5.1
docker pull thingsboard/tb-coap-transport:3.5.1
docker pull thingsboard/tb-lwm2m-transport:3.5.1
docker pull thingsboard/tb-snmp-transport:3.5.1

git clone -b release-3.5 https://github.com/thingsboard/thingsboard.git
cd thingsboard/docker

./docker-create-log-folders.sh
./docker-install-tb.sh --loadDemo
./docker-start-services.sh
