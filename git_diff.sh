#!/bin/bash

TARGET="${1}"

# Get running version
SRL_VERSION=`gnmic -a ${TARGET} --skip-verify get --path /system/information/version -u admin -p NokiaSrl1! -e json_ietf | jq -r '.[].updates[].values[] | split("-")[0]'`

# Checkout YANG models
rm -rf /tmp/srlinux-yang-models/
git clone https://github.com/nokia/srlinux-yang-models.git /tmp/srlinux-yang-models/

# Get latest version available
LATEST_VERSION=`cd /tmp/srlinux-yang-models/ && git tag --sort=committerdate | tail -1`

if [[ "${SRL_VERSION}" != "${LATEST_VERSION}" ]]; then
 cd /tmp/srlinux-yang-models/ && git diff ${SRL_VERSION} ${LATEST_VERSION}
else
 echo "'${TARGET}' is running the latest version '${LATEST_VERSION}'"
fi
