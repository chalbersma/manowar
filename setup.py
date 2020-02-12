#!/usr/bin/env python3

'''
An attempt to make a ghetto packaging script.
'''

# pylint: skip-file

import setuptools
import sys
import os
import subprocess # nosec
import datetime
import logging
import glob

import git

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("setup.py")

current_repo = git.Repo()

if current_repo.bare:
    print("Something went wrong Repo is Bare, Failing the Build.")
    sys.exit(1)
else:

    env_keys = dict(os.environ).keys()

    travis_keys = [key for key in env_keys if key.startswith("TRAVIS")]

    for key in travis_keys:
        print("{} : {}".format(key, os.environ[key]))

    travis_repo = os.environ.get("TRAVIS_REPO_SLUG", "NOTRAVIS")
    travis_pull_req = os.environ.get("TRAVIS_PULL_REQUEST", "UNKNOWN")
    travis_branch = os.environ.get("TRAVIS_BRANCH", "UNKNOWN")
    travis_event_type = os.environ.get("TRAVIS_EVENT_TYPE", "UNKNOWN")
    travis_tag = os.environ.get("TRAVIS_TAG", "")
    travis_build_no = os.environ.get("TRAVIS_BUILD_NUMBER", 0)

    print(travis_build_no)

# Set Default Version
version_base = datetime.datetime.today().strftime("%Y.%m.%d")
upload_to_pypi = False


# My Known Good Repository
if travis_repo == "chalbersma/manowar" and len(travis_tag) > 0:
    # Make a Version Fix here that equls the tag
    print("Tagged Branch : {}".format(travis_tag))
    version = travis_tag
    upload_to_pypi = "prod"
elif travis_repo == "chalbersma/manowar":
    # This is in my repo and
    version = "{}-dev{}".format(version_base, travis_build_no)
    print("VERSION : {}".format(version))
    upload_to_pypi = "stag"
else:
    upload_to_pypi = False
    version = "{}-dev0".format(version_base)

# Only upload on 3.6.x Matrix
if "3.7" != "{}.{}".format(sys.version_info[0], sys.version_info[1]):
    print("Version is : {} which doesn't equal 3.7.x not uploading".format(sys.version_info))
    upload_to_pypi = False

if upload_to_pypi is not False and upload_to_pypi == "stag":
    os.environ["TWINE_USERNAME"] = "__token__"
    os.environ["TWINE_PASSWORD"] = os.environ.get("PYPI_STAG_TOKEN", "whasit")
    twine_cmd = ["twine", "upload", "--repository-url", "https://test.pypi.org/legacy/", "dist/*"]
elif upload_to_pypi is not False and upload_to_pypi == "prod":
    os.environ["TWINE_USERNAME"] = "__token__"
    os.environ["TWINE_PASSWORD"] = os.environ.get("PYPI_PROD_TOKEN", "whasit")
    twine_cmd = ["twine", "upload", "dist/*"]
else:
    # Not Uploading
    pass


print("VERSION : {}".format(version))

with open("README.md", "r") as fh:
    long_description = fh.read()

# Get Version

setuptools.setup(
    name="manowar_server",
    version=version,
    author="Chris Halbersma",
    author_email="chris+manowar@halbersma.us",
    description="Server and Data Collection Components",
    license="BSD-2-Clause",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chalbersma/manowar",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Security"
    ],
    install_requires=[
        "PyYAML",
        "flask",
        "flask_cors",
        "pymysql",
        "manowar_agent",
        "jsonschema",
        "packaging",
        "cvss",
        "cpe",
        "feedparser",
        "pyjq",
        "yoyo-database-migrations",
        "pylxd",
        "colorama"
    ],
    scripts=["manowar_server", ],
    data_files=[("etc/manowar", ["etc/manowar/manoward.yaml.sample"]),
                ("etc/manowar/salt", ["etc/manowar/salt/master",
                                      "etc/manowar/salt/roster.sample",
                                      "etc/manowar/salt/Saltfile"]
                ),
                ("etc/manowar/salt/log", ["etc/manowar/salt/log/keep"]),
                ("etc/manowar/salt/pillar", ["etc/manowar/salt/pillar/keep",
                                             "etc/manowar/salt/pillar/top.sls"]
                ),
                ("etc/manowar/salt/pki_dir", ["etc/manowar/salt/pki_dir/keep"]),
                ("etc/manowar/salt/ssh", ["etc/manowar/salt/ssh/keep"]),
                ("etc/manowar/salt/state", ["etc/manowar/salt/state/keep",
                                            "etc/manowar/salt/state/top.sls"]),
                ("share/manoward/yoyo_steps", ["yoyo_steps/yoyo.ini.sample"]),
                ("share/manoward/yoyo_steps/migrations", glob.glob("yoyo_steps/migrations/*"))
               ]
)

if upload_to_pypi is not False:

    print("Attempting to Upload to PyPi : {}".format(upload_to_pypi))

    result = subprocess.check_call(twine_cmd) # nosec

    print("Result : {}".format(result))
else:
    print("Not attempting to Upload.")
