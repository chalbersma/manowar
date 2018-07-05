# Installing

Minimal Installation Instructions here for Demo.

## Pre-Requisites

* Install dependencies

    sudo apt-get -y install openssh-server python3-pip python-dev shellcheck mariadb-server mariadb-client jq openjdk-7-jre graphviz
    sudo pip3 install --upgrade setuptools
    sudo pip3 install bandit pylint paramiko pymysql colorama flask flask_cors jsonschema feedparser lxml pika mkdocs
    sudo gem install mdl

* [Install MariaDB 10.x on your system](https://mariadb.com/kb/en/library/installing-mariadb-deb-files/)

* Install an SSH Key with the user you're going to run the system with.

    ssh-keygen -y -f ~/.ssh/id_rsa > ~/.ssh/id_rsa.pub

* Add it to authroized keys

    cat ~/.ssh/id_rsa.pub > ~/.ssh/authorized_keys
    
* Ensure SSHD is Running

    sudo service ssh restart
    # Test SSH Functionality
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null localhost echo test

* Add Fake Hosts to /etc/hosts

    echo -e "127.0.0.1      testbox1.vrt" | sudo tee -a /etc/hosts
    echo -e "127.0.0.1      testbox2.vrt" | sudo tee -a /etc/hosts
    echo -e "127.0.0.1      testbox3.vrt" | sudo tee -a /etc/hosts
    echo -e "127.0.0.1      testbox4.vrt" | sudo tee -a /etc/hosts
    echo -e "127.0.0.1      testbox5.vrt" | sudo tee -a /etc/hosts
    

* Run the Travis script for setting up db Schema. This will use default passwords and should
  not be utilized in production

    ./travis/db_setup.sh

## Optional: Code Checks

Optionally, you can run the code checks here to ensure that nothing has broken.

    ./travis/testing.sh
    ./travis/swagger_test.sh

## Spin Up API Servers (Flask)

* Spin up the UI (in Dev Mode).

    ./ui.py -d -c ./travis/artifacts/ui.ini > ui.log &
    
* Spin up the Storage API (in Dev Mode).

    ./storageAPI.py -d -c ./travis/artifacts/storageAPI.ini > /home/travis/sapi.log &

## Test Scheduler

* Scheduler Test

    ./schedule2.py -c travis/artifacts/scheduler.ini -b travis/artifacts/servers4.csv -V

## Test Analyze

* Analyze Test

    ./analyze.py -a travis/artifacts/audit.d -c travis/artifacts/analyze.ini
    ./collate.py -c travis/artifacts/collate.ini -V

