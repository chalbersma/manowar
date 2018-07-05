#!/bin/bash 

# 
# FPM Build Script
#
# Should use FPM to build the package.
#

VERSION=2.3.2

fpm -s dir -t deb -n vdms-stingcell -v ${VERSION} -C ./stingcell/  \
  --before-install ./setup/stingcell-preinstall.sh \
  --after-remove ./setup/stingcell-postuninstall.sh \
  --vendor VDMS \
  --license Undefined \
  --maintainer chris.halbersma@verizondigitalmedia.com \
  --url http://vdms.io/ \
  --description "Collection Agent for Jellyfish Software" \
  --architecture x86_64 \
  --category utilities \
  --package ./debs \
  --depends python3-requests 
