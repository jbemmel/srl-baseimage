# srl-baseimage
Modified SR Linux container image with some personal enhancements and modifications

* Enable passwordless login for all user accounts by adding a custom global authorized_keys file
* Fix some cosmetic issues with show command output (e.g. column widths)
* Allow 4-byte private ASNs in extended communities, in the range 4<2>00000000..4<2>99999999 (typo in Yang models)
* Install gnmic and pygnmi packages
* Extend CLI with environment variables and dynamic resolution of config references, to enable easy copy&paste of config snippets

# VXLAN traceroute
The code contains a [sample custom tools command](https://github.com/jbemmel/srl-baseimage/blob/main/vxlan_traceroute.py) to invoke standard Linux traceroute with parameters tailored to EVPN VXLAN troubleshooting:
* User selects a VXLAN L2 network-instance (mac-vrf) by name (using auto completion)
* Plugin determines the corresponding VNI and list of VTEP IPs announcing the same VNI
* Plugin invokes 'traceroute' sourced from system0 IP, targeting either all or a single VTEP

![image](https://user-images.githubusercontent.com/2031627/154775401-1148692f-f671-4aa2-922f-d32355d91da1.png)

# gRPC Network Operations Interface (gNOI)

Some notes and quick start on gNOI:
* [SR Linux documentation for R22.11](https://documentation.nokia.com/srlinux/22-11/SR_Linux_Book_Files/SysMgmt_Guide/gnoi-interface.html)
* Install [gnoic client](https://github.com/karimra/gnoic):
```bash
bash -c "$(curl -sL https://get-gnoic.kmrd.dev)"
```
* Sample command:
```bash
gnoic system time -a clab-spine-leaf-evpn-leaf1 --skip-verify -u admin -p NokiaSrl1!
```
Output:
```
+----------------------------------+-----------------------------------------+---------------------+
|           Target Name            |                  Time                   |      Timestamp      |
+----------------------------------+-----------------------------------------+---------------------+
| clab-spine-leaf-evpn-leaf1:57400 | 2023-02-22 09:11:25.600358126 -0600 CST | 1677078685600358126 |
+----------------------------------+-----------------------------------------+---------------------+
```

# gNMIc customizations

The repo contains a sample config file for gnmic, to add the BGP peer description to session state change events for SR OS.
To use:
```
gnmic --config gnmic_add_peer_description.yaml subscribe
```
