#!/bin/bash

# Add Stingcell Group
/usr/sbin/groupadd -r stingcell

# Add Stingcell User
/usr/sbin/useradd -d /var/lib/stingcell -m -s /bin/false -g stingcell -r -c 'Stingcell Client User' stingcell 

# Create Stingcell Log Location
mkdir -p /var/log/stingcell
chown stingcell.stingcell /var/log/stingcell
