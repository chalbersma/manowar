#!/bin/bash


set -x

# Salt Santity Checker
cd -v /home/travis/build/chalbersma/manowar/travis/artifacts/salt

salt-ssh -W \* test.ping -l debug


