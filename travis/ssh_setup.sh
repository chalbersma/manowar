#!/usr/bin/env bash

ls ~/.ssh

# Create a new ssh key
ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa

# Copy this to the Salt Key Location
cp -v ~/.ssh/id_rsa /home/travis/build/chalbersma/manowar/travis/artifacts/salt/ssh/salt_key
cp -v ~/.ssh/id_rsa.pub /home/travis/build/chalbersma/manowar/travis/artifacts/salt/ssh/salt_key.pub

# Authorized Keys
cat ~/.ssh/id_rsa.pub > ~/.ssh/authorized_keys

# Ensure SSHD Enabled
sudo service ssh restart


timeout 1m ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null localhost echo test

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

ssh -o StrictHostKeyChecking=accept-new testbox1.vrt
ssh -o StrictHostKeyChecking=accept-new testbox2.vrt
ssh -o StrictHostKeyChecking=accept-new testbox3.vrt
ssh -o StrictHostKeyChecking=accept-new testbox4.vrt
ssh -o StrictHostKeyChecking=accept-new testbox5.vrt
