# Multi-tenant Internet services using an EVPN VXLAN fabric

This lab illustrates an advanced, realistic deployment of Internet facing services for multiple tenants. Each tenant is using one or more separate IP-VRF instances, and *Route Leaking* is used to aggregate all these services towards the public Internet

Key feature highlights:
* IPv4/v6 route leaking
* EVPN VXLAN fabric with Route Reflectors and multi-homed LAGs
* VRRP v4/v6 tenant servers

## Run this lab
```
sudo clab deploy --reconfigure
```

# Ping test to VRRP VIP
```
docker exec -it clab-spine-leaf-evpn-client ping -c3 10.0.0.100
```

## Same for IPv6
```
docker exec -it clab-spine-leaf-evpn-client ping6 -c3 2001:1::100
```

# Force failover of VRRP1 (master) to VRRP2
```
docker exec -it clab-spine-leaf-evpn-vrrp1 ip link set dev lo down
```

## Note on symmetric IRB
When using asymmetric IRB (i.e. no VXLAN L3 interface inside IP VRF, not using EVPN RT5 routes) it was found that after failover to VRRP2, Leaf1 would not install the EVPN route to the VIP in its routing table

## Note on virtual router IDs
![image](https://github.com/jbemmel/srl-self-organizing/assets/2031627/27c47077-75b3-46de-9c2c-a619dc1b8246)

In this setup, it is important to ensure that the virtual router id for the anycast gateway and the virtual router id for VRRP (keepalived) are different.
