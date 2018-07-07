#!/usr/bin/env bash

# Setup SSH Things for Testing
ssh-keygen -y -f ~/.ssh/id_rsa > ~/.ssh/id_rsa.pub

# Authorized Keys
cat ~/.ssh/id_rsa.pub > ~/.ssh/authorized_keys
-
# Ensure SSHD Enabled
sudo service ssh restart

cat /etc/ssh/sshd_config

ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null localhost echo test

testsshsuccess=$?

if [[ ${testsshsuccess} -gt 0 ]] ; then
  echo -e "Error with Test SSH'ing"
  exit 1
fi


# Add Fake Hosts to /etc/hosts
echo -e "127.0.0.1	testbox1.vrt" | sudo tee -a /etc/hosts
echo -e "127.0.0.1	testbox5.vrt" | sudo tee -a /etc/hosts
echo -e "127.0.0.1	testbox4.vrt" | sudo tee -a /etc/hosts
echo -e "127.0.0.1	testbox3.vrt" | sudo tee -a /etc/hosts
echo -e "127.0.0.1	testbox2.vrt" | sudo tee -a /etc/hosts