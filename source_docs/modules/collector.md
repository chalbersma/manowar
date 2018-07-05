# Collector

By itself `collector.py` is actually a simple module. It simply parses some configs
to tell itself what it out to do. Then runs and parses those commands on individual
hosts. It's main usage is to get called by `schedule2.py` over and over again to
do the collections.

![Collector Arch](/plantuml/collector_diagram.svg)

## Collection Configuration

Collection configuration is by default stored in svn in the `collector.ini` file.
Here is an example of a collection :

```ini
[packages]
; Remote Collection Command
multi=TRUE
collection=dpkg --list | grep -E '^ii' | awk '{print $2"\011"$3}'
```

Collections can be either single dimentional or multi-dimensional. Single dimentional
lines will get stored as just one "default" collection subtype. Multidimentional
ones will get stored with each line being treated as a `subtype value` combo where
whitespace seperates the two items.

Here are the top few results of what this command produces. Note how each package
will end up being it's own subtype. :

```
> dpkg --list | grep -E '^ii' | awk '{print $2"\011"$3}' | head
accountsservice 0.6.42-0ubuntu3.1
acl     2.2.52-3build1
acpi-support    0.142
acpid   1:2.0.28-1ubuntu1
adduser 3.113+nmu3ubuntu5
adium-theme-ubuntu      0.3.4-0ubuntu4
adobe-flash-properties-gtk      1:20180313.1-0ubuntu0.17.10.1
adobe-flashplugin       1:20180313.1-0ubuntu0.17.10.1
adwaita-icon-theme      3.26.0-0ubuntu2
aisleriot       1:3.22.2-0ubuntu1
```

Interpolation is a thing. When the config is parsed any `%` character is going to
be specially viewed. If you need a `%` character (see example below) you'll need to
write a `%%`. You'll find it useful with stat and date commands.
Here is an example of a collection that uses this:

```ini
[ssh-host-key-age]
; Grabs a hash of the SSH host key
multi=TRUE
collection=stat -c %%n"     "%%Y /etc/ssh/*.pub | tr '[/.]' '_'
```

## SSH

Python's [Paramiko](http://www.paramiko.org/) module is used to log into each host
and the jellyfish ssh key that get's installed in salt is generally used to log in.
Currently that key is managed by hand on the jellyfish machine and it's public half
is delivered via salt.

## Example

Below is an example of a collection being ran manually and the data it produces
(truncated to protect the innocent and the scrollwheels). Note that because of the
uniqueness of bast servers a good chunk of collections don't work out of the box.

```json
{
    "collection_data": {
        "boottime": {
            "default": "Tue Mar 20 00:00:00 UTC 2018"
        },
        "cpu-info": {
            "Architecture:": "x86_64",
            "BogoMIPS:": "4000.00",
            "Byte": "Order: Little Endian",
            "CPU": "MHz: 2000.000",
            "CPU(s):": "8",
            "Core(s)": "per socket: 4",
            "Hypervisor": "vendor: VMware",
            "L1d": "cache: 32K",
            "L1i": "cache: 32K",
            "L2": "cache: 256K",
            "L3": "cache: 15360K",
            "Model:": "45",
            "NUMA": "node0 CPU(s): 0-7",
            "On-line": "CPU(s) list: 0-7",
            "Socket(s):": "2",
            "Stepping:": "7",
            "Thread(s)": "per core: 1",
            "Vendor": "ID: GenuineIntel",
            "Virtualization": "type: full"
        },
        "host_host": {
            "HOSTNAME": "host1.host",
            "POP": "N/A",
            "SRVTYPE": "N/A",
            "STATUS": "N/A",
            "UBERID": "N/A"
        },
        "pci-info": {
            "00:00.0": "Host bridge: Intel Corporation 440BX/ZX/DX - 82443BX/ZX/DX Host bridge (rev 01)",
            "00:01.0": "PCI bridge: Intel Corporation 440BX/ZX/DX - 82443BX/ZX/DX AGP bridge (rev 01)",
            "00:07.0": "ISA bridge: Intel Corporation 82371AB/EB/MB PIIX4 ISA (rev 08)",
            "00:07.1": "IDE interface: Intel Corporation 82371AB/EB/MB PIIX4 IDE (rev 01)",
            "00:07.3": "Bridge: Intel Corporation 82371AB/EB/MB PIIX4 ACPI (rev 08)",
            "00:07.7": "System peripheral: VMware Virtual Machine Communication Interface (rev 10)",
            "00:0f.0": "VGA compatible controller: VMware SVGA II Adapter",
            "00:11.0": "PCI bridge: VMware PCI bridge (rev 02)",
            "00:15.0": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:15.1": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:15.2": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:15.3": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:15.4": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:15.5": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:15.6": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:15.7": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:16.0": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:16.1": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:16.2": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:16.3": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:16.4": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:16.5": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:16.6": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:16.7": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:17.0": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:17.1": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:17.2": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:17.3": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:17.4": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:17.5": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:17.6": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:17.7": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:18.0": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:18.1": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:18.2": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:18.3": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:18.4": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:18.5": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:18.6": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "00:18.7": "PCI bridge: VMware PCI Express Root Port (rev 01)",
            "03:00.0": "Ethernet controller: VMware VMXNET3 Ethernet Controller (rev 01)"
        },
        "reboot-needed": {
            "default": "NO-REBOOT-REQUIRED"
        },
        "release": {
            "default": "trusty"
        },
        "repositories-hash": {
            "default": "1fe60f07c344e2a4e9459be05aed9c12+8"
        },
        "rkernel": {
            "default": "4.4.0-103-generic"
        }
    },
    "collection_hostname": "host1.host",
    "collection_status": "SSH SUCCESS",
    "collection_timestamp": 1522187510,
    "connection_string": "chalbersma@1.1.1.1",
    "ip_intel": [
        {
            "ip": "1.1.1.1",
            "iptype": "host4"
        }
    ],
    "ipv6_val_error": "Found IPV6 Address would not Validateillegal IP address string passed to inet_pton",
    "pop": "N/A",
    "srvtype": "N/A",
    "status": "N/A",
    "uber_id": "N/A"
}
```
