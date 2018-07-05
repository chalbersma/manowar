#!/bin/bash

# Here be pre-build steps if needed

echo -e 'Pre Steps'

echo -e "Enabling Trusty Backports for Shellcheck"

echo -e "deb http://archive.ubuntu.com/ubuntu trusty-backports main restricted universe multiverse" | sudo tee /etc/apt/sources.list.d/backports.list

echo -e "Enabling Mariadb 10.2 Repo"

sudo apt-get install software-properties-common

sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db

sudo add-apt-repository 'deb [arch=amd64] http://sfo1.mirrors.digitalocean.com/mariadb/repo/10.2/ubuntu trusty main'

sudo apt-get update


# Allow self ssh login
ssh-keygen -y -f ~/.ssh/id_rsa > ~/.ssh/id_rsa.pub

# Authorized Keys
cat ~/.ssh/id_rsa.pub > ~/.ssh/authorized_keys

# Ensure SSHD Enabled
sudo service ssh restart

ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null localhost echo test

# Add Fake Hosts to /etc/hosts
echo -e "127.0.0.1	testbox1.vrt" | sudo tee -a /etc/hosts
echo -e "127.0.0.1	testbox5.vrt" | sudo tee -a /etc/hosts
echo -e "127.0.0.1	testbox4.vrt" | sudo tee -a /etc/hosts
echo -e "127.0.0.1	testbox3.vrt" | sudo tee -a /etc/hosts
echo -e "127.0.0.1	testbox2.vrt" | sudo tee -a /etc/hosts

# Make Clean Docs
rm -rf docs/

mkdir docs
