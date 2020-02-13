#!/usr/bin/env python3

import argparse
import logging
# Need this until pylxd actually works
import subprocess # nosec
import json
import time
import os
import os.path
import shlex

import pylxd
import yaml

_currently_supported_platforms = {"centos8" : {"lxc" : "images:centos/8",
                                               "prefix" : "centeig",
                                               "postfix" : "c8n"},
                                  "centos7" : {"lxc" : "images:centos/7",
                                               "prefix" : "centsev",
                                               "postfix" : "c7n"},
                                  "ubuntubionic" :  {"lxc" : "images:ubuntu/bionic",
                                                  "prefix" : "ububionic",
                                                  "postfix" : "bio"},
                                  "ubuntuxenail" : {"lxc" : "images:ubuntu/xenial",
                                                  "prefix" : "ubuxenial",
                                                  "postfix" : "xen"},
                                  "ubuntufocal" : {"lxc" : "images:ubuntu/focal",
                                                  "prefix" : "ubufocal",
                                                  "postfix" : "foc"}
                                }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--roster", help="Existing Roster File", default=None)
    parser.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])
    parser.add_argument("-p", "--print", action="store_true", help="Print New Roster in JSON", default=False)
    parser.add_argument("-k", "--pubkey", default="etc/manowar/salt/ssh/salt_key.pub", help="Public Key to Install in Test Roster", type=str)
    parser.add_argument("-c", "--count", help="number of boxes", default=1, type=int)

    args = parser.parse_args()
    
    
    VERBOSE = len(args.verbose)
    
    if VERBOSE == 0:
        logging.basicConfig(level=logging.ERROR)

    elif VERBOSE == 1:
        logging.basicConfig(level=logging.WARNING)

    elif VERBOSE == 2:
        logging.basicConfig(level=logging.INFO)

    elif VERBOSE > 2:
        logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger()

    logger.info("Welcome to Mocker LXC")
    
    logger.info("Going to Create {} Boxes".format(args.count))
    
    if args.roster is not None and os.path.isfile(args.roster) is True:
        # Load an Existing Roster File in
        with open(args.roster, "r") as existing_roster_obj:
            existing_roster = yaml.safe_load(existing_roster_obj)
    else:
        existing_roster = dict()
    
    with open(args.pubkey, "r") as pubkey_file_obj:
        pubkey_string = pubkey_file_obj.read().strip("\n")
        
        logger.debug("The Key to be installed :\n{}".format(pubkey_string))
        
        
    lxd_client = pylxd.Client()
    
    all_current_containers = lxd_client.containers.all()
    all_container_names = [container.name for container in all_current_containers]
    
    logger.debug("Currently Specified Containsers:\n{}".format("\n".join(all_container_names)))
    
    for iteration in range(1, args.count+1):
        for platform, platform_args in _currently_supported_platforms.items():
            
            this_location = platform_args.get("postfix", platform[0:3])
            this_platform = platform_args.get("prefix", platform)
            
            this_roster_id = "{}{:03}{}".format(this_platform,
                                                 iteration,
                                                 this_location)
                                             
            this_roster_args = {"uri" : "mown://mowtest:{}:{}::{}?owner=testowner&status=prod".format(this_location,
                                                                                                      this_platform,
                                                                                                      this_roster_id),
                                "sudo" : platform_args.get("use_sudo", True),
                                "user" : "{}".format(platform_args.get("platform_user", "root"))}
                                             
            logger.info("Found Platform : {}".format(platform))
            logger.debug("Creating Box : {}".format(this_roster_id))
            
            if this_roster_id in all_container_names:
                logger.debug("Ignoring Box {} as it's already created.".format(this_roster_id))
            else:
                logger.info("Creating new Container {}".format(this_roster_id))
                
                # PYLXD is Busted
                create_command = "lxc launch {} {}".format(platform_args["lxc"],
                                                           shlex.quote(this_roster_id))
                
                logger.debug("Launch Command : \n{}".format(create_command))
                
                cmd_args = {"stdout" : subprocess.PIPE,
                            "executable" : "/bin/bash",
                            "shell" : True}
                
                                         
                logger.info("Spinning up Container for {}".format(this_roster_id))
                try:
                    
                    run_result = subprocess.run(create_command, **cmd_args) # nosec
                    
                except Exception as container_error:
                    logger.error("Container error on {}".format(this_roster_id))
                    logger.debug("Error : {}".format(container_error))
                else:
                    
                    logger.debug("Create Output:\n{}".format(run_result.stdout))
                    
                    try:
                        run_result.check_returncode()
                    except Exception as process_error:
                        logger.error("Unable to Startup Container with id of {}".format(this_roster_id))
                        logger.debug("Python Error : {}".format(process_error))
                        logger.debug("Error : {}".format(run_result.stderr))
                    else:
                    
                        logger.info("Created Container {}".format(this_roster_id))
                        
                        # Let Creation happen
                        time.sleep(60)
                        
                        # Grab IP Of Created Container
                        ipv4_command = "lxc list {} --columns 4 --format=csv".format(shlex.quote(this_roster_id))
                        
                        ipv4_run_result = subprocess.run(ipv4_command, **cmd_args) # nosec
                        
                        # Inject new Roster Args
                        this_roster_args["host"] = str(ipv4_run_result.stdout.decode("utf-8").split()[0])
                        
                        existing_roster[this_roster_id] = this_roster_args
                    
                    finally:
                        
                        # Just do these,. ignore failures
                        # Should Add Key for most unix like systems
                        # New platforms need new things
                        # God help me if windows comes to lxc
                        dumb_key_sequence = ["yum -y install openssh-server openssh-clients python3 sudo",
                                             "apt-get install -y openssh-server",
                                             "service sshd start",
                                             "service ssh start",
                                             "mkdir -p ~/.ssh",
                                             "touch ~/.ssh/authorized_keys",
                                             "echo -e \"{}\" >> ~/.ssh/authorized_keys".format(pubkey_string),
                                             "chmod go-w ~/",
                                             "chmod 700 ~/.ssh",
                                             "chmod 600 ~/.ssh/authorized_keys"]
                        
                        for dks in dumb_key_sequence:
                            
                            this_command = "lxc exec {} -- /bin/bash -c '{}'".format(shlex.quote(this_roster_id),
                                                                                  dks)
                            
                            logger.debug("Running bad command : {}".format(this_command))
                            this_result = subprocess.run(this_command, **cmd_args) # nosec
                            
                            
                            logger.debug("STDOUT: {}".format(this_result.stdout))
                            logger.debug("STDERR: {}".format(this_result.stderr))
                        
        
        if iteration > 5:
            logger.warning("Let's not Get Crazy Here.")
            break
            
        
    if args.roster is not None:
        logger.info("Writing Roster file to {}".format(args.roster))
        
        with open(args.roster, "w") as roster_file_write:
            yaml.dump(existing_roster, roster_file_write, sort_keys=True)
    
    if args.print is True:
        print(json.dumps(existing_roster, default=str, sort_keys=True, indent=2))
    
    
