ARG SR_LINUX_RELEASE
FROM ghcr.io/nokia/srlinux:$SR_LINUX_RELEASE

ARG P1="/usr/local/lib/python3.6/site-packages:/usr/local/lib64/python3.6/site-packages"
ARG P2="/opt/rh/rh-python36/root/usr/lib/python3.6/site-packages/sdk_protos"
ARG P3="/usr/lib/python3.6/site-packages/sdk_protos"
ARG P4="/opt/srlinux/python/virtual-env/lib/python3.6/site-packages"
ENV AGENT_PYTHONPATH="$P1:$P2:$P3:$P4"

RUN sudo curl -sL https://github.com/karimra/gnmic/releases/download/v0.20.0/gnmic_0.20.0_Linux_x86_64.rpm -o /tmp/gnmic.rpm && sudo yum localinstall -y /tmp/gnmic.rpm

# Install pyGNMI to /usr/local/lib[64]/python3.6/site-packages
# RUN sudo yum-config-manager --disable ipdcentos ipdrepo ius && sudo yum clean all
RUN sudo yum install -y python3-pip gcc-c++ jq pylint && \
    sudo python3 -m pip install pip --upgrade && \
    sudo python3 -m pip install pygnmi pylint-protobuf sre_yield

# Fix gNMI path key order until patch is accepted
# RUN sudo sed -i.orig 's/path_elem.key.items()/sorted(path_elem.key.items())/g' /usr/local/lib/python3.6/site-packages/pygnmi/client.py

# Add CLI enhancements
COPY ./mgmt_cli_engine_command_loop.py /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli_engine/command_loop.py

# Define custom aliases for admin user, including Cisco style show CLI
RUN sudo mkdir -p /home/admin && printf '%s\n' \
  '[alias]' \
  '"containerlab save" = "save file /etc/opt/srlinux/config.json /"' \
  '"sh int {int}" = "show /interface"' \
  \
> /home/admin/.srlinuxrc

# Apply IPv6 column width fixes
RUN sudo sed -i.orig 's/(ancestor_keys=False, print_on_data=True)/(ancestor_keys=False,print_on_data=True,widths=[28])/g' \
    /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/bgp_evpn*_routes_report.py

# Fix 4-byte ASN private range to allow target:4200000000:12345
# up to 4294967295
# Preserve order of communities
RUN cd /opt/srlinux/models/srl_nokia/models/ && \
    sudo sed -i.orig 's/4\[0-1\]\[0-9\]{7}/42[0-8][0-9]{7}|4[0-1][0-9]{8}/g' routing-policy/srl_nokia-policy-types.yang common/srl_nokia-common.yang && \
    sudo sed -i.orig 's/leaf-list member {/leaf-list member { ordered-by user;/g' routing-policy/srl_nokia-routing-policy.yang

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
