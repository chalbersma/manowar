# Manowar

> Manowar, it stores info about your servers and analyzes it for you if you ask it to.

## Description

Manowar is a tool designed to help people profile and analyze their server
fleets for for various things. With is companion tool, audittools
it can check environments for a series of common vulnerabilities that one might
wish to check against. 

The goal is to build and centrally store a commonlly formatted
set of data for each server in your environment that you can use to analyze
and answer questions quickly about your environment with.

## Install

Installation is unfortunately manual at the moment. There are some pidgin examples
of how to install in the `travis/` directory. In the future, ports to replace
EdgeCast specific deployment code should be added.

## Security

[Bandit](https://github.com/PyCQA/bandit) is utilized in travis for automatic
code scanning. Generally, if your python code doesn't pass a bandit check it won't be
accepted in. Additionally, [shellcheck](https://www.shellcheck.net/) is utilized 
for bash code, same rules apply.

## Contributing

Please refer to the `contributing.md` file for information about how to get involved. We welcome issues, questions, and pull requests. Pull Requests are welcome.

## Maintainers

Chris Halbersma : chris+manowar@halbersma.us

## Usage

See the `install.md` file for instruction on how to get the project running. The apis will by default start on localhost
on ports 5000 and 5001. 

## License

Code is made available under a [BSD-2-Clause](https://opensource.org/licenses/BSD-2-Clause) license (see `LICENSE` file). 
