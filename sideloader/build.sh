#!/bin/bash

cp -a $REPO ./build/$NAME

${PIP} install -r $REPO/malaria24/requirements.txt

