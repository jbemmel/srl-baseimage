ARG SR_LINUX_RELEASE
FROM ghcr.io/nokia/srlinux:$SR_LINUX_RELEASE

RUN sudo curl -sL https://github.com/karimra/gnmic/releases/download/v0.17.1/gnmic_0.17.1_Linux_x86_64.rpm -o /tmp/gnmic.rpm && sudo yum localinstall -y /tmp/gnmic.rpm

# Install pyGNMI to /usr/local/lib[64]/python3.6/site-packages
# RUN sudo yum-config-manager --disable ipdcentos ipdrepo ius && sudo yum clean all
RUN sudo yum install -y python3-pip gcc-c++ && \
    sudo python3 -m pip install pip --upgrade && \
    sudo python3 -m pip install pygnmi

# Add CLI enhancements
COPY ./mgmt_cli_engine_command_loop.py /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli_engine/command_loop.py

# Apply IPv6 column width fixes
RUN sudo sed -i.orig 's/(ancestor_keys=False, print_on_data=True)/(ancestor_keys=False,print_on_data=True,widths=[28])/g' \
    /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/bgp_evpn*_routes_report.py

# Fix 4-byte ASN private range to allow target:4200000000:12345
RUN cd /opt/srlinux/models/srl_nokia/models/ && sudo sed -i.orig 's/4\[0-1\]\[0-9\]{7}/4[0-2][0-9]{8}/g' routing-policy/srl_nokia-policy-types.yang common/srl_nokia-common.yang

# Add global authorized_keys file
RUN sudo sed -i.orig 's|.ssh/authorized_keys|.ssh/authorized_keys /etc/ssh/authorized_keys|g' /etc/ssh/sshd_config
# This file must be owned by root:root with 644 permissions
COPY --chmod=0644 ./authorized_keys /etc/ssh/authorized_keys

# Using a build arg to set the release tag, set a default for running docker build manually
ARG SRL_CUSTOMBASE_RELEASE="[custom build]"
ENV SRL_CUSTOMBASE_RELEASE=$SRL_CUSTOMBASE_RELEASE
