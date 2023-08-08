#!/usr/bin/python
###########################################################################
# Description:
#
# Copyright (c) 2019 Nokia
###########################################################################
from srlinux.location import build_path
from srlinux.mgmt.cli import CliPlugin, RequiredPlugin, KeyCompleter
from srlinux.syntax import Syntax

from .bgp_ipv4_exact_route_detail_report import BgpIpv4ExactDetailFilter
from .bgp_ipv4_exact_route_report import BgpIpv4ExactFilter
from .bgp_ipv4_community_route_report import BgpIpv4CommunityFilter # JvB added
from .bgp_ipv4_routes_summary_report import BgpIpv4Filter
from .bgp_ipv6_exact_route_detail_report import BgpIpv6ExactDetailFilter
from .bgp_ipv6_exact_route_report import BgpIpv6ExactFilter
from .bgp_ipv6_routes_summary_report import BgpIpv6Filter
from .bgp_neigh_advertised_routes_report import BgpNeighAdvertisedRoutesFilter
from .bgp_neigh_received_routes_report import BgpNeighReceivedRoutesFilter
from .bgp_neighbor_detail_report import BgpNeighborDetailFilter
from .bgp_neighbor_summary_report import BgpNeighborSummaryFilter
from .bgp_neighbor_summary_report import BgpNeighMaintModeFilter
from .bgp_evpn_received_routes_report import BgpEvpnReceivedRoutesFilter
from .bgp_evpn_advertised_routes_report import BgpEvpnAdvertisedRoutesFilter
from .bgp_summary_report import BgpSummaryFilter
from .bgp_evpn_reports import EvpnSummary
from .bgp_evpn_route_type_report import EvpnRouteType
from .bgp_evpn_instance_report import BgpEvpnInstance
from .bgp_vpn_instance_report import BgpVpnInstance


class Plugin(CliPlugin):
    '''
        Adds bgp routes ipv4 summary show reports.
    '''

    def get_required_plugins(self):
        return [
            # bgp_reports adds 'show network-instance' so it must be loaded first
            # to add our new plugin beneath it.
            RequiredPlugin(module='srlinux', plugin='netinst_reports')
        ]

    def load(self, cli, **_kwargs):
        network = cli.show_mode.root.get_command('network-instance')
        protocols = network.get_command('protocols')

        bgp = protocols.add_command(Syntax('bgp'), update_location=True)
        bgp.add_command(
            BgpSummaryFilter().get_syntax(),
            update_location=False,
            callback=BgpSummaryFilter().print,
            schema=BgpSummaryFilter().get_data_schema(),
        )
        self.add_bgp_neighbor_subcmds(bgp)

        routes = bgp.add_command(Syntax('routes'))
        self.add_ipv4_subcmds(routes)
        self.add_ipv6_subcmds(routes)
        self.add_evpn_subcmds(routes)

        bgp_evpn = protocols.add_command(Syntax('bgp-evpn'), update_location=True, filter=feature_evpn)
        bgp_evpn.add_command(Syntax('bgp-instance')
                             .add_unnamed_argument('instance', suggestions=KeyCompleter(path=self._get_bgp_evpn_instance)),
                             callback=BgpEvpnInstance().print,
                             schema=BgpEvpnInstance().get_data_schema())

        bgp_vpn = protocols.add_command(Syntax('bgp-vpn'), update_location=True)
        bgp_vpn.add_command(Syntax('bgp-instance')
                             .add_unnamed_argument('instance', suggestions=KeyCompleter(path=self._get_bgp_vpn_instance)),
                             callback=BgpVpnInstance().print,
                             schema=BgpVpnInstance().get_data_schema())

    def add_ipv4_subcmds(self, routes):
        ipv4_unicast = routes.add_command(Syntax('ipv4'))

        prefix_ipv4 = ipv4_unicast.add_command(
            Syntax('prefix')
            .add_unnamed_argument('prefix', suggestions=KeyCompleter(path=self._get_ipv4_prefix_path))
            .add_boolean_argument('or-longer'),
            callback=self._prefix_exact_v4_summary_print_maybe,
            schema=BgpIpv4ExactFilter().get_data_schema()
        )
        ipv4_unicast.add_command(
            BgpIpv4Filter().get_syntax(),
            update_location=False,
            callback=BgpIpv4Filter().print,
            schema=BgpIpv4Filter().get_data_schema(),
        )
        prefix_ipv4.add_command(
            BgpIpv4ExactDetailFilter().get_syntax(),
            update_location=False,
            callback=BgpIpv4ExactDetailFilter().print,
            schema=BgpIpv4ExactDetailFilter().get_data_schema(),
        )

        # JvB added
        ipv4_unicast.add_command(
            BgpIpv4CommunityFilter().get_syntax(),
            callback=BgpIpv4CommunityFilter().print,
            schema=BgpIpv4CommunityFilter().get_data_schema(),
        )

    def add_ipv6_subcmds(self, routes):
        ipv6_unicast = routes.add_command(Syntax('ipv6'))
        prefix_ipv6 = ipv6_unicast.add_command(
            Syntax('prefix')
            .add_unnamed_argument('prefix', suggestions=KeyCompleter(path=self._get_ipv6_prefix_path))
            .add_boolean_argument('or-longer'),
            callback=self._prefix_exact_v6_summary_print_maybe,
            schema=BgpIpv6ExactFilter().get_data_schema()
        )
        ipv6_unicast.add_command(
            BgpIpv6Filter().get_syntax(),
            update_location=False,
            callback=BgpIpv6Filter().print,
            schema=BgpIpv6Filter().get_data_schema(),
        )
        prefix_ipv6.add_command(
            BgpIpv6ExactDetailFilter().get_syntax(),
            update_location=False,
            callback=BgpIpv6ExactDetailFilter().print,
            schema=BgpIpv6ExactDetailFilter().get_data_schema(),
        )

    def add_evpn_subcmds(self, routes):
        evpn = routes.add_command(Syntax('evpn'))
        evpn_rt = evpn.add_command(Syntax('route-type', help='Show EVPN route-type report'))

        evpn_rt.add_command(Syntax('summary', help='Show All EVPN route summary report'),
            update_location=False,
            callback=EvpnSummary()._print_all,
            schema=EvpnSummary().get_data_schema())

        #evpn_rt.add_command(Syntax('detail', help='Show All EVPN route detail report'),
        #    update_location=False,
        #    callback=EvpnRouteType()._print_all,
        #    schema=EvpnRouteType().get_data_schema())

        eth_ad_cmd = evpn_rt.add_command(Syntax('1', help='Ethernet Auto-Discovery Routes')
                                     .add_named_argument('rd', default='*', suggestions=KeyCompleter(path=self._get_ethernet_ad_routes, keyname='route-distinguisher'))
                                     .add_named_argument('esi', default='*', suggestions=KeyCompleter(path=self._get_ethernet_ad_routes, keyname='esi'))
                                     .add_named_argument('ethernet-tag-id', default='*', suggestions=KeyCompleter(path=self._get_ethernet_ad_routes, keyname='ethernet-tag-id'))
                                     .add_named_argument('neighbor', default='*', suggestions=KeyCompleter(path=self._get_ethernet_ad_routes, keyname='neighbor'))
                                     )
        mac_ip_cmd = evpn_rt.add_command(Syntax('2', help='MAC-IP Advertisement Routes')
                                     .add_named_argument('rd', default='*', suggestions=KeyCompleter(path=self._get_mac_ip_routes, keyname='route-distinguisher'))
                                     .add_named_argument('mac-address', default='*', suggestions=KeyCompleter(path=self._get_mac_ip_routes, keyname='mac-address'))
                                     .add_named_argument('ip-address', default='*', suggestions=KeyCompleter(path=self._get_mac_ip_routes, keyname='ip-address'))
                                     .add_named_argument('ethernet-tag-id', default='*', suggestions=KeyCompleter(path=self._get_mac_ip_routes, keyname='ethernet-tag-id'))
                                     .add_named_argument('neighbor', default='*', suggestions=KeyCompleter(path=self._get_mac_ip_routes, keyname='neighbor'))
                                     )
        imet_cmd = evpn_rt.add_command(Syntax('3', help='IMET Routes')
                                     .add_named_argument('rd', default='*', suggestions=KeyCompleter(path=self._get_imet_routes, keyname='route-distinguisher'))
                                     .add_named_argument('originating-router', default='*', suggestions=KeyCompleter(path=self._get_imet_routes, keyname='originating-router'))
                                     .add_named_argument('ethernet-tag-id', default='*', suggestions=KeyCompleter(path=self._get_imet_routes, keyname='ethernet-tag-id'))
                                     .add_named_argument('neighbor', default='*', suggestions=KeyCompleter(path=self._get_imet_routes, keyname='neighbor'))
                                   )
        eth_seg_cmd = evpn_rt.add_command(Syntax('4', help='Ethernet Segment Routes')
                                     .add_named_argument('rd', default='*', suggestions=KeyCompleter(path=self._get_ethernet_segment_routes, keyname='route-distinguisher'))
                                     .add_named_argument('esi', default='*', suggestions=KeyCompleter(path=self._get_ethernet_segment_routes, keyname='esi'))
                                     .add_named_argument('originating-router', default='*', suggestions=KeyCompleter(path=self._get_ethernet_segment_routes, keyname='originating-router'))
                                     .add_named_argument('neighbor', default='*', suggestions=KeyCompleter(path=self._get_ethernet_segment_routes, keyname='neighbor'))
                                   )
        ip_prefix_cmd = evpn_rt.add_command(Syntax('5', help='IP Prefix Routes')
                                     .add_named_argument('rd', default='*', suggestions=KeyCompleter(path=self._get_ipprefix_routes, keyname='route-distinguisher'))
                                     .add_named_argument('ethernet-tag-id', default='*', suggestions=KeyCompleter(path=self._get_ipprefix_routes, keyname='ethernet-tag-id'))
                                     .add_named_argument('prefix', default='*', suggestions=KeyCompleter(path=self._get_ipprefix_routes, keyname='ip-prefix'))
                                     .add_named_argument('neighbor', default='*', suggestions=KeyCompleter(path=self._get_ipprefix_routes, keyname='neighbor'))
                                   )

        eth_ad_cmd.add_command(Syntax('summary', help='Show All EVPN route summary report'),
            update_location=False,
            callback=EvpnSummary()._print_1,
            schema=EvpnSummary().get_data_schema())

        eth_ad_cmd.add_command(Syntax('detail', help='Show EVPN Ethernet Auto-discovery route detail report'),
            update_location=False,
            callback=EvpnRouteType()._print_1,
            schema=EvpnRouteType().get_data_schema())

        mac_ip_cmd.add_command(Syntax('summary', help='Show All EVPN MAC-IP Advt route summary report'),
            update_location=False,
            callback=EvpnSummary()._print_2,
            schema=EvpnSummary().get_data_schema())

        mac_ip_cmd.add_command(Syntax('detail', help='Show EVPN MAC-IP Advt route detail report'),
            update_location=False,
            callback=EvpnRouteType()._print_2,
            schema=EvpnRouteType().get_data_schema())

        imet_cmd.add_command(Syntax('summary', help='Show All EVPN IMET route summary report'),
            update_location=False,
            callback=EvpnSummary()._print_3,
            schema=EvpnSummary().get_data_schema())

        imet_cmd.add_command(Syntax('detail', help='Show EVPN IMET route detail report'),
            update_location=False,
            callback=EvpnRouteType()._print_3,
            schema=EvpnRouteType().get_data_schema())

        eth_seg_cmd.add_command(Syntax('summary', help='Show All EVPN Ethernet Segment route summary report'),
            update_location=False,
            callback=EvpnSummary()._print_4,
            schema=EvpnSummary().get_data_schema())

        eth_seg_cmd.add_command(Syntax('detail', help='Show EVPN Ethernet Segment route detail report'),
            update_location=False,
            callback=EvpnRouteType()._print_4,
            schema=EvpnRouteType().get_data_schema())

        ip_prefix_cmd.add_command(Syntax('summary', help='Show All EVPN IP Prefix route summary report'),
            update_location=False,
            callback=EvpnSummary()._print_5,
            schema=EvpnSummary().get_data_schema())

        ip_prefix_cmd.add_command( Syntax('detail', help='Show EVPN IP Prefix route detail report'),
            update_location=False,
            callback=EvpnRouteType()._print_5,
            schema=EvpnRouteType().get_data_schema())


    def add_bgp_neighbor_subcmds(self, bgp):
        neighbor = bgp.add_command(
            Syntax('neighbor')
            .add_unnamed_argument('peer-address', default='*', suggestions=KeyCompleter(path=self._get_neighbor_path)),
            update_location=True,
            callback=self._neighbor_summary_print_maybe,
            schema=BgpNeighborSummaryFilter().get_data_schema(),
        )
        neighbor.add_command(
            BgpNeighborDetailFilter().get_syntax(),
            update_location=False,
            callback=BgpNeighborDetailFilter().print,
            schema=BgpNeighborDetailFilter().get_data_schema(),
        )
        received_routes = neighbor.add_command(Syntax('received-routes'))
        received_routes.add_command(
            BgpEvpnReceivedRoutesFilter().get_syntax(),
            update_location=False,
            callback=BgpEvpnReceivedRoutesFilter().print,
            schema=BgpEvpnReceivedRoutesFilter().get_data_schema(),
        )
        received_routes.add_command(
            BgpNeighReceivedRoutesFilter().get_syntax_v4(),
            update_location=False,
            callback=BgpNeighReceivedRoutesFilter().print_v4,
            schema=BgpNeighReceivedRoutesFilter().get_data_schema(),
        )
        received_routes.add_command(
            BgpNeighReceivedRoutesFilter().get_syntax_v6(),
            update_location=False,
            callback=BgpNeighReceivedRoutesFilter().print_v6,
            schema=BgpNeighReceivedRoutesFilter().get_data_schema(),
        )
        advertised_routes = neighbor.add_command(Syntax('advertised-routes'))
        advertised_routes.add_command(
            BgpEvpnAdvertisedRoutesFilter().get_syntax(),
            update_location=False,
            callback=BgpEvpnAdvertisedRoutesFilter().print,
            schema=BgpEvpnAdvertisedRoutesFilter().get_data_schema(),
        )
        advertised_routes.add_command(
            BgpNeighAdvertisedRoutesFilter().get_syntax_v4(),
            update_location=False,
            callback=BgpNeighAdvertisedRoutesFilter().print_v4,
            schema=BgpNeighAdvertisedRoutesFilter().get_data_schema(),
        )
        advertised_routes.add_command(
            BgpNeighAdvertisedRoutesFilter().get_syntax_v6(),
            update_location=False,
            callback=BgpNeighAdvertisedRoutesFilter().print_v6,
            schema=BgpNeighAdvertisedRoutesFilter().get_data_schema(),
        )
        neighbor.add_command(
            BgpNeighMaintModeFilter().get_syntax(),
            update_location=False,
            callback=BgpNeighMaintModeFilter().print,
            schema=BgpNeighMaintModeFilter().get_data_schema(),
        )

    def _neighbor_summary_print_maybe(self, state, arguments, output, **_kwargs):
        if state.is_intermediate_command:
            return

        BgpNeighborSummaryFilter().print(state, arguments, output, **_kwargs)

    def _prefix_exact_v4_summary_print_maybe(self, state, arguments, output, **_kwargs):
        if state.is_intermediate_command:
            return

        BgpIpv4ExactFilter().print(state, arguments, output, **_kwargs)

    def _prefix_exact_v6_summary_print_maybe(self, state, arguments, output, **_kwargs):
        if state.is_intermediate_command:
            return

        BgpIpv6ExactFilter().print(state, arguments, output, **_kwargs)

    def _get_ipv4_prefix_path(self, arguments):
        return build_path(
            '/network-instance[name={name}]/bgp-rib/ipv4-unicast/local-rib/routes[prefix=*][neighbor=*][origin-protocol=*]',
            name=arguments.get('network-instance', 'name')
        )

    def _get_ipv6_prefix_path(self, arguments):
        return build_path(
            '/network-instance[name={name}]/bgp-rib/ipv6-unicast/local-rib/routes[prefix=*][neighbor=*][origin-protocol=*]',
            name=arguments.get('network-instance', 'name')
        )

    def _get_ethernet_ad_routes(self, arguments):
        return build_path('/network-instance[name={name}]/bgp-rib/evpn/rib-in-out/rib-in-post/ethernet-ad-routes[route-distinguisher={rd}][esi={esi}][ethernet-tag-id={etag}][neighbor={peer}]',
                          name=arguments.get('network-instance', 'name'),
                          rd=arguments.get('1', 'rd'),
                          esi=arguments.get('1', 'esi'),
                          etag=arguments.get('1', 'ethernet-tag-id'),
                          peer=arguments.get('1', 'neighbor'),
                          )

    def _get_mac_ip_routes(self, arguments):
        return build_path(
            '/network-instance[name={name}]/bgp-rib/evpn/rib-in-out/rib-in-post/mac-ip-routes[route-distinguisher={rd}][mac-length=*][mac-address={mac}][ip-address={ip}][ethernet-tag-id={etag}][neighbor={peer}]',
            name=arguments.get('network-instance', 'name'),
            rd=arguments.get('2', 'rd'),
            mac=arguments.get('2', 'mac-address'),
            ip=arguments.get('2', 'ip-address'),
            etag=arguments.get('2', 'ethernet-tag-id'),
            peer=arguments.get('2', 'neighbor'),
            )

    def _get_imet_routes(self, arguments):
        return build_path(
            '/network-instance[name={name}]/bgp-rib/evpn/rib-in-out/rib-in-post/imet-routes[route-distinguisher={rd}][originating-router={orouter}][ethernet-tag-id={etag}][neighbor={peer}]',
            name=arguments.get('network-instance', 'name'),
            rd=arguments.get('3', 'rd'),
            orouter=arguments.get('3', 'originating-router'),
            etag=arguments.get('3', 'ethernet-tag-id'),
            peer=arguments.get('3', 'neighbor'),
        )

    def _get_ethernet_segment_routes(self, arguments):
        return build_path(
            '/network-instance[name={name}]/bgp-rib/evpn/rib-in-out/rib-in-post/ethernet-segment-routes[route-distinguisher={rd}][esi={esi}][originating-router={orouter}][neighbor={peer}]',
            name=arguments.get('network-instance', 'name'),
            rd=arguments.get('4', 'rd'),
            esi=arguments.get('4', 'esi'),
            orouter=arguments.get('4', 'originating-router'),
            peer=arguments.get('4', 'neighbor'),
        )

    def _get_ipprefix_routes(self, arguments):
        return build_path(
            '/network-instance[name={name}]/bgp-rib/evpn/rib-in-out/rib-in-post/ip-prefix-routes[route-distinguisher={rd}][ethernet-tag-id={etag}][ip-prefix-length=*][ip-prefix={ip}][neighbor={peer}]',
            name=arguments.get('network-instance', 'name'),
            etag=arguments.get('5', 'ethernet-tag-id'),
            ip=arguments.get('5', 'prefix'),
            peer=arguments.get('5', 'neighbor'),
            rd=arguments.get('5', 'rd'),
        )

    def _get_neighbor_path(self, arguments):
        return build_path(
            '/network-instance[name={name}]/protocols/bgp/neighbor[peer-address=*]',
            name=arguments.get('network-instance', 'name')
        )

    def _get_bgp_evpn_instance(self, arguments):
        return build_path('/network-instance[name={name}]/protocols/bgp-evpn/bgp-instance[id=*]',
            name=arguments.get('network-instance', 'name')
        )

    def _get_bgp_vpn_instance(self, arguments):
        return build_path('/network-instance[name={name}]/protocols/bgp-vpn/bgp-instance[id=*]',
            name=arguments.get('network-instance', 'name')
        )

def get_route_type():
    return [i for i in range(1, 6)]

def feature_vxlan(state, node):
    return state.system_features.vxlan

def feature_evpn(state, node):
    return state.system_features.evpn
