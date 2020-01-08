#!/bin/bash

set -x

## Setup DB Schema

sudo mysql -u root -e "show full processlist;"

sudo bash -c "mysql -u root < echo create database manowar2"
schema_success=$?

echo -e "Copying Yoyo Travis Config"

ls -l

cp -v ./travis/artifacts/yoyo.ini ./yoyo_migrations/

echo -e "Using Yoyo Travis Configs"

cd yoyo_migrations

yoyo apply
