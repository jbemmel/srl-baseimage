ARG SR_LINUX_RELEASE
FROM ghcr.io/nokia/srlinux:$SR_LINUX_RELEASE

RUN sudo curl -sL https://github.com/karimra/gnmic/releases/download/v0.17.1/gnmic_0.17.1_Linux_x86_64.rpm -o /tmp/gnmic.rpm && sudo yum localinstall -y /tmp/gnmic.rpm

RUN printf '%s\n' \
  '#!/bin/bash' \
  '' \
  'mkdir -p /etc/opt/srlinux/appmgr && cp /home/appmgr/* /etc/opt/srlinux/appmgr/' \
  'exit $?' \
  \
> /tmp/42.sh && sudo mv /tmp/42.sh /opt/srlinux/bin/bootscript/42_sr_copy_custom_appmgr.sh && \
  sudo chmod a+x /opt/srlinux/bin/bootscript/42_sr_copy_custom_appmgr.sh

# Install pyGNMI to /usr/local/lib[64]/python3.6/site-packages
# RUN sudo yum-config-manager --disable ipdcentos ipdrepo ius && sudo yum clean all
RUN sudo yum install -y python3-pip gcc-c++ && \
    sudo python3 -m pip install pip --upgrade && \
    sudo python3 -m pip install pygnmi

# Add CLI enhancements
COPY ./mgmt_cli_engine_command_loop.py /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli_engine/command_loop.py

# Apply IPv6 column width fixes
RUN sudo sed -i 's/(ancestor_keys=False, print_on_data=True)/(ancestor_keys=False,print_on_data=True,widths=[28])/g' \
    /opt/srlinux/python/virtual-env/lib/python3.6/site-packages/srlinux/mgmt/cli/plugins/reports/bgp_evpn*_routes_report.py

# Fix 4-byte ASN private range to allow target:4200000000:12345
RUN cd /opt/srlinux/models/srl_nokia/models/ && sudo sed -ir 's/4\[0-1\]/4[0-2]/g' routing-policy/srl_nokia-policy-types.yang common/srl_nokia-common.yang

# Using a build arg to set the release tag, set a default for running docker build manually
ARG SRL_CUSTOMBASE_RELEASE="[custom build]"
ENV SRL_CUSTOMBASE_RELEASE=$SRL_CUSTOMBASE_RELEASE
