# Canonical CVE

This is actually a simple module. Give this command a CVE number and it will
query Ubuntu's CVE site to get any associated package data for the CVE in question.
The following is an example with
[CVE-2018-8885](https://people.canonical.com/~ubuntu-security/cve/2018/CVE-2018-8885.html).

```shell
> ./canonical_cve.py CVE-2018-8885 | jq '.'
{
  "references": [
    "https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-8885",
    "https://launchpad.net/bugs/1753772",
    "https://usn.ubuntu.com/usn/usn-3607-1"
  ],
  "title": "CVE-2018-8885",
  "priority": "Medium",
  "packages": {
    "screen-resolution-extra": {
      "package_name": "screen-resolution-extra",
      "package_upstream_status": "needs-triage",
      "releases": {
        "precise": {
          "release": "precise",
          "status": "dne",
          "version": false
        },
        "trusty": {
          "release": "trusty",
          "status": "released",
          "version": "0.17.1.1~14.04.1"
        },
        "xenial": {
          "release": "xenial",
          "status": "released",
          "version": "0.17.1.1~16.04.1"
        },
        "artful": {
          "release": "artful",
          "status": "released",
          "version": "0.17.1.1"
        },
        "bionic": {
          "release": "bionic",
          "status": "needed",
          "version": false
        }
      }
    }
  }
}
```

## Usage

This is used in a few other modules (like bass in jellyfishaudits) to get information
about CVEs. And is used in sherlockfish to do semi-automatic, on demand audits
of information.

## Future

This is a webscraper. If ever Ubuntu updates it's formatting we'll need to update our
scraping. It's probably a good idea to instead of scraping the website go straight to
the [source](https://bazaar.launchpad.net/~ubuntu-security/ubuntu-cve-tracker/master/view/head:/active/CVE-2018-8885)
for our future needs.
