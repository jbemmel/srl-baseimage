ARG SR_LINUX_RELEASE
FROM ghcr.io/nokia/srlinux:$SR_LINUX_RELEASE

ARG P1="/usr/local/lib/python3.6/site-packages:/usr/local/lib64/python3.6/site-packages"
ARG P2="/opt/rh/rh-python36/root/usr/lib/python3.6/site-packages/sdk_protos"
ARG P3="/usr/lib/python3.6/site-packages/sdk_protos"
ARG P4="/opt/srlinux/python/virtual-env/lib/python3.6/site-packages"
ENV AGENT_PYTHONPATH="$P1:$P2:$P3:$P4"

RUN sudo rm -rf /etc/yum.repos.d/epel* /etc/yum.repos.d/elrepo* && \
    sudo yum clean all && \
    sudo curl -sL https://github.com/karimra/gnmic/releases/download/v0.24.4/gnmic_0.24.4_Linux_x86_64.rpm -o /tmp/gnmic.rpm && \
    sudo yum localinstall -y /tmp/gnmic.rpm && sudo rm -f /tmp/gnmic.rpm

# Install pyGNMI to /usr/local/lib[64]/python3.6/site-packages
# RUN sudo yum-config-manager --disable ipdcentos ipdrepo ius && sudo yum clean all
# RUN sudo yum install -y python3-pip gcc-c++ jq pylint diffutils && \
#     sudo python3 -m pip install pip --upgrade && \
#     sudo python3 -m pip install --force-reinstall --no-deps grpcio && \
#     sudo PYTHONPATH=$AGENT_PYTHONPATH python3 -m pip install pygnmi pylint-protobuf sre_yield

# Install (only) some custom tools
RUN sudo yum install -y jq diffutils && sudo pip3 install pylint

# Copy custom built pygnmi and dependencies, install into /usr/local. Need to upgrade pip
COPY --from=pygnmi /tmp/wheels /tmp/wheels
RUN sudo python3 -m pip install --upgrade pip && \
    sudo python3 -m pip install --no-cache --no-index /tmp/wheels/* && \
    sudo rm -rf /tmp/wheels

# Add pylint and sre_yield as before
RUN sudo PYTHONPATH=$AGENT_PYTHONPATH python3 -m pip install pygnmi pylint-protobuf sre_yield

# Fix gNMI path key order until patch is accepted
# RUN sudo sed -i.orig 's/path_elem.key.items()/sorted(path_elem.key.items())/g' /usr/local/lib/python3.6/site-packages/pygnmi/client.py

# Add CLI enhancements
COPY ./mgmt_cli_engine_command_loop.py /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli_engine/command_loop.py
COPY ./traceroute.py /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/traceroute.py
COPY ./arpnd_reports.py /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/arpnd_reports.py

# Integrate custom vxlan-traceroute CLI commands
COPY ./vxlan_traceroute.py /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/
RUN sudo sh -c ' echo -e "vxlan_traceroute = srlinux.mgmt.cli.plugins.vxlan_traceroute:Plugin" \
  >> /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux-0.1-py3.6.egg-info/entry_points.txt'

# Define custom aliases for admin user, including Cisco style show CLI
RUN sudo mkdir -p /home/admin && printf '%s\n' \
  '[alias]' \
  '"containerlab save" = "save file /etc/opt/srlinux/config.json /"' \
  '"sh int {int}" = "show /interface"' \
  '"arp-nd-entries" = "info from state /platform linecard 1 forwarding-complex 0 datapath xdp resource arp-nd-entries"' \
  \
> /home/admin/.srlinuxrc

# Apply IPv6 column width fixes
RUN sudo sed -i.orig 's/(ancestor_keys=False, print_on_data=True)/(ancestor_keys=False,print_on_data=True,widths=[28])/g' \
    /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/bgp_evpn*_routes_report.py

# Fix ISIS ipv4 column width
RUN sudo sed -i.orig 's/borders=None/borders=None,widths={"Ip Address":15}/g' \
    /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/isis_adjacency_report.py

# Reduce route summary column widths to have more for IP addresses
RUN sudo sed -i.orig "s/'Tag ID' : 10,/'Tag ID':10,'Route-distinguisher':15,'VNI':8,'neighbor':10,'IP-address':39,/g" \
    /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/bgp_evpn_reports.py

# Fix index column for MAC address all
RUN sudo sed -i.orig 's/10,/11, # JvB increased/g' \
    /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/bridge_table_mac_table_report.py


# Fix 4-byte ASN private range to allow target:4200000000:12345
# up to 4294967295
# Preserve order of communities
# Remove 'mandatory' for TLS on gNMI? Does not work
RUN cd /opt/srlinux/models/srl_nokia/models/ && \
    sudo sed -i.orig 's/4\[0-1\]\[0-9\]{7}/42[0-8][0-9]{7}|4[0-1][0-9]{8}/g' routing-policy/srl_nokia-policy-types.yang common/srl_nokia-common.yang && \
    sudo sed -i.orig 's/leaf-list member {/leaf-list member { ordered-by user;/g' routing-policy/srl_nokia-routing-policy.yang
#    sudo sed -i.orig 's|false() or (/srl_nokia-lldp:system/lldp/interface\[srl_nokia-lldp:name=current()/../../../srl_nokia|true() or (/srl_nokia-lldp:system/lldp/interface\[srl_nokia-lldp:name=current()/../../../srl_nokia|g' interfaces/srl_nokia-interfaces-l2cp.yang

RUN sudo yum install -y lldpad

# sudo sed -i.orig 's/mandatory true/mandatory false/g' system/srl_nokia-gnmi-server.yang

# Disallow RD:0 - doesn't work
# sudo sed -i "0,/3}|\[0-9])';/s//3}|\[1-9\])'; \/\/ JvB disallow ip:0 RD/" common/srl_nokia-common.yang

# Fix ESI sensitivity to capitalization
RUN sudo sed -i.orig 's/esi=ethseg.esi/esi=ethseg.esi.lower()/g' \
    /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/system_network_instance_reports.py

# Fix bgp route nexthop displayed in CLI, 2 instances
RUN sudo sed -i.orig 's/routes.prefix, nexthop/routes.prefix, attr.next_hop if attr.next_hop!="0.0.0.0" else nexthop/g' \
    /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/bgp_neigh_advertised_routes_report.py

# Fix boot script errors
RUN sudo sed -i.orig 's/!srl/! srl/g' /opt/srlinux/bin/bootscript/05_sr_createuser.sh && \
    sudo sed -i.orig 's/python/python3/g' /opt/srlinux/bin/bootscript/05_sr_createuser.sh

# Make 'type' also a key for network instances? Doesn't work
# sudo sed -i.orig 's/key "name";/key "name type";/' network-instance/srl_nokia-network-instance.yang

# Add global authorized_keys file
RUN sudo sed -i.orig 's|.ssh/authorized_keys|.ssh/authorized_keys /etc/ssh/authorized_keys|g' /etc/ssh/sshd_config
# This file must be owned by root:root with 644 permissions
COPY --chmod=0644 ./authorized_keys /etc/ssh/authorized_keys

# Reduce per-client ICMP error rate limit from 1000ms to 100ms
# Does not work
# RUN echo "net.ipv4.icmp_ratelimit=100" | sudo tee -a /etc/sysctl.conf

# Using a build arg to set the release tag, set a default for running docker build manually
ARG SRL_CUSTOMBASE_RELEASE="[custom build]"
ENV SRL_CUSTOMBASE_RELEASE=$SRL_CUSTOMBASE_RELEASE
