#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''


def jreadconfig(configfile, literal_eval=True) :
    '''
    jellyfish read config
    Will parse the config file given and return 100% ast literal evaled items.
    Unless marked as non desired.
    '''

    from configparser import ConfigParser
    import ast
    import time

    # Read Config File and Return Dict of Info
    now_time=int(time.time())
    defaults= { "time" : str(now_time) }

    try:
        # Read Our INI with our data collection rules
        config = ConfigParser(defaults)
        #config = ConfigParser()
        config.read(configfile)
    except Exception as e: # pylint: disable=broad-except, invalid-name
        sys.exit('Bad configuration file {}'.format(e))

    # DB Config Items
    config_dict=dict()
    for section in config:
        config_dict[section]=dict()
        for item in config[section]:
            if literal_eval :
                config_dict[section][item] = ast.literal_eval(config[section][item])
            else :
                config_dict[section][item] = config[section][item]
    #print(config_dict)

    return config_dict

