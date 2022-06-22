#!/bin/bash

if [ $# -eq 0 ]
  then
  # "No arguments supplied"
  export VERSION_NAME=`git describe | sed 's/\(.*\)-.*/\1/'`
else
  export VERSION_NAME=$1
fi
echo "Setting version to $VERSION_NAME"
sed -i "s/PROG_VERSION=.*$/PROG_VERSION='${VERSION_NAME}'/" pydatview/main.py
