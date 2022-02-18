#!/usr/bin/python
###########################################################################
# Description:
# Custom CLI command to perform traceroute in the context of EVPN VXLAN fabrics:
# * Select a L2 VNI context (customer service)
# * auto-complete VTEP IP addresses within that VNI service, auto-select source IP
# * disable DNS resolution
#
# Copyright (c) 2021-2022 Nokia
###########################################################################
from srlinux.mgmt.cli import ExecuteError, KeyCompleter
from srlinux.mgmt.cli.tools_plugin import ToolsPlugin
from srlinux.mgmt.cli.required_plugin import RequiredPlugin

from srlinux.syntax import Syntax
from srlinux.location import build_path
from srlinux import child_process
from srlinux.schema import DataStore

import sys, logging

#
# Standard traceroute in the context of EVPN VXLAN fabrics
#
class Plugin(ToolsPlugin):

    # Provide list of plugins that must be loaded before this one
    def get_required_plugins(self):
        return [RequiredPlugin("tools_mode")]

    # Define where this command exists in the command hierarchy in sr_cli
    def on_tools_load(self, state):
        # Could also add it under /tools network-instance
        if state.system_features.vxlan:
           root = state.command_tree.tools_mode.root
           root.add_command(self._get_syntax(state), update_location=False, callback=do_vxlan_traceroute)
        # system = state.command_tree.tools_mode.root.get_command('system')
        # system.add_command(self._get_syntax(), update_location=False, callback=do_service_ping)
        else:
            logging.warning( "VXLAN feature not enabled for this system" )

    # Helper function to get arguments and help strings for this plugin command
    def _get_syntax(self,state):
        syntax = Syntax("vxlan-traceroute", help="Traces ECMP paths to other VXLAN VTEPs in a given L2 overlay service")
        syntax.add_named_argument('mac-vrf', help="target mac-vrf used to lookup the VNI",
          suggestions=KeyCompleter(path='/network-instance[name=*]')) # Cannot select type=mac-vrf only?

        # Lookup vxlan interface for given mac-vrf - seems to deadlock
        def _get_vteps_in_vrf(arguments):
          mac_vrf = arguments.get_or('mac-vrf','*')
          # logging.info( f"_get_path args={arguments} mac_vrf={mac_vrf}" )
          if mac_vrf!='*':
             vxlan_intf = get_vxlan_interface(state,mac_vrf)
             tun = vxlan_intf.split('.')
          else:
             tun = ['*','*']
          return build_path(f'/tunnel-interface[name={tun[0]}]/vxlan-interface[index={tun[1]}]/bridge-table/multicast-destinations/destination[vtep=*][vni=*]')

        syntax.add_named_argument('vtep', default='*', help='Optional VTEP IP, default=all',
           suggestions=KeyCompleter(path='/tunnel-interface[name=*]/vxlan-interface[index=*]/bridge-table/multicast-destinations/destination[vtep=*]') )

        # syntax.add_boolean_argument('debug', help="Enable additional debug output")

        # TODO add 'count' argument, default 3
        return syntax

def get_vxlan_interface(state,mac_vrf):
   path = build_path(f'/network-instance[name={mac_vrf}]/protocols/bgp-evpn/bgp-instance[id=1]/vxlan-interface')
   data = state.server_data_store.get_data(path, recursive=True)
   return data.network_instance.get().protocols.get().bgp_evpn.get().bgp_instance.get().vxlan_interface

# Callback that runs when the plugin is run in sr_cli
def do_vxlan_traceroute(state, input, output, arguments, **_kwargs):
    logging.info( f"do_vxlan_traceroute arguments={arguments}" )

    mac_vrf = arguments.get('vxlan-traceroute', 'mac-vrf')
    vtep = arguments.get('vxlan-traceroute', 'vtep')
    # debug = arguments.get('vxlan-service-ping', 'debug')

    def get_vni(vxlan_intf):
       tun = vxlan_intf.split('.')
       path = build_path(f'/tunnel-interface[name={tun[0]}]/vxlan-interface[index={tun[1]}]/ingress/vni')
       data = state.server_data_store.get_data(path, recursive=True)
       return data.tunnel_interface.get().vxlan_interface.get().ingress.get().vni

    def get_system0_vtep_ip():
       path = build_path('/interface[name=system0]/subinterface[index=0]/ipv4/address')
       data = state.server_data_store.get_data(path, recursive=True)
       return data.interface.get().subinterface.get().ipv4.get().address.get().ip_prefix.split('/')[0]

    # Need to access State
    def get_evpn_vteps(vxlan_intf):
       logging.info( f"vxlan-service-ping: Listing VTEPs associated with VXLAN interface {vxlan_intf}" )
       tun = vxlan_intf.split('.')
       path = build_path(f'/tunnel-interface[name={tun[0]}]/vxlan-interface[index={tun[1]}]/bridge-table/multicast-destinations/destination')
       data = state.server.get_data_store( DataStore.State ).get_data(path, recursive=True)
       return [ p.vtep for p in data.tunnel_interface.get().vxlan_interface.get().bridge_table.get().multicast_destinations.get().destination.items() ]

    vxlan_intf = get_vxlan_interface(state,mac_vrf)
    vni = get_vni(vxlan_intf)
    local_vtep = get_system0_vtep_ip()
    dest_vteps = [ vtep ] if vtep!='*' else get_evpn_vteps(vxlan_intf)

    for ip in dest_vteps:
      # Don't need sudo, hardcoded namespace name 'default'
      # Wait 100ms between probes, to avoid packet drops due to rate limits
      cmd = f"ip netns exec srbase-default /usr/bin/traceroute -n --sendwait=100 -s {local_vtep} {ip}"
      logging.info( f"vxlan-traceroute: bash {cmd}" )
      exit_code = child_process.run( cmd.split(), output=output )
