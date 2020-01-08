#!/bin/bash

set -x

## Setup DB Schema
sudo mysql -u root -e "show full processlist;"
sudo mysql -u root -e "show variables;"

sudo bash -c "mysql -u root < echo create database manowar2"
schema_success=$?

echo -e "Copying Yoyo Travis Config"

ls -l /var/run/mysqld/

file ./travis/artifacts/yoyo.ini

cp -v ./travis/artifacts/yoyo.ini ./yoyo_steps/

echo -e "Using Yoyo Travis Configs"

cd ./yoyo_steps

yoyo apply
