# srl-baseimage
Modified SR Linux container image with some personal enhancements and modifications

* Enable passwordless login for all user accounts by adding a custom global authorized_keys file
* Fix some cosmetic issues with show command output (e.g. column widths)
* Allow 4-byte private ASNs in extended communities, in the range 4<2>00000000..4<2>99999999 (typo in Yang models)
* Install gnmic and pygnmi packages
* Extend CLI with environment variables and dynamic resolution of config references, to enable easy copy&paste of config snippets
