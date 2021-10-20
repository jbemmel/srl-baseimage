#!/bin/sh

# Exclude TTL=0 ICMP errors from rate limiting by the kernel, default = 6168
sysctl -w net.ipv4.icmp_ratemask=4120
