#!/bin/bash


set -x

# Salt Santity Checker
cd /home/travis/build/chalbersma/manowar/travis/artifacts/salt

salt-ssh -W testbox1.vrt test.ping -l debug


