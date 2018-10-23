#!/bin/bash
export VERSION_NAME=`git describe | sed 's/\(.*\)-.*/\1/'`
echo "Setting version to $VERSION_NAME"
sed -i "s/PROG_VERSION=.*$/PROG_VERSION='${VERSION_NAME}'/" pydatview/pydatview.py
