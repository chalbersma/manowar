#!/usr/bin/env python3

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="stingcell",
    version="0.0.1",
    author="Chris Halbersma",
    author_email="chris+manowar@halbersma.us",
    description="Package to Add as a Collector",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chalbersma/manowar",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent"
    ],
)
