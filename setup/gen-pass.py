#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import os
import binascii

rand = binascii.b2a_hex(os.urandom(16)).decode()

print(rand)
