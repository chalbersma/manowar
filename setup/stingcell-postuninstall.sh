#!/bin/bash

# Remove Stingcell User
userdel stingcell

# Remove Stingcell Group
groupdel stingcell 

# Remove Log Location
rm -r /var/log/stingcell
