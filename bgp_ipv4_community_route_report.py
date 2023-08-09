#!/usr/bin/python
###########################################################################
# Description:
#
# Copyright (c) 2019 Nokia
###########################################################################
from enum import Enum, auto
from srlinux import data
from srlinux.data import Data, Formatter, TagValuePrinter, Indent
from srlinux.mgmt.cli.key_completer import KeyCompleter
from srlinux.location import build_path
from srlinux.mgmt.cli import ParseError, ExecuteError
from srlinux.schema import FixedSchemaRoot
from srlinux.strings import split_before
from srlinux.syntax import Syntax
from srlinux.syntax.argument import ArgumentArrayType

import logging

class BgpIpv4CommunityFilter(object):
    '''
        Adds 'show network-instance default protocols bgp routes ipv4 community xyz' command.

        Example output:

        A:s1# show network-instance default protocols bgp routes ipv4 community 65001:1 
---------------------------------------------------------------------------------------------
Show report for the BGP routes with target community "65001:1" in network-instance "default"
---------------------------------------------------------------------------------------------
Matching Paths: 2
  Path 1: 1.1.1.1/32 <Best,Valid,Used,>
    Route source    : neighbor 10.0.0.2
    Route Preference: MED is -, LocalPref is 100
    BGP next-hop    : 10.0.0.2
    Path            :  ? [65001]
    Communities     : 65001:1
  Path 2: 10.0.0.0/24 <Valid,>
    Route source    : neighbor 10.0.0.2
    Route Preference: MED is -, LocalPref is 100
    BGP next-hop    : 10.0.0.2
    Path            :  i [65001]
    Communities     : 65001:1
    '''

    __slots__ = (
        '_arguments',
        '_filter_function',
        '_requested_community',
    )

    def _get_ipv4_community_path(self, arguments):
        # Only 4-byte community values
        return build_path(
            '/network-instance[name={name}]/bgp-rib/attr-sets/attr-set[index=*]/communities/community',
            name=arguments.get('network-instance', 'name')
        )

    def get_syntax(self):
        return (Syntax('community').add_unnamed_argument('community',
          # array_type=ArgumentArrayType.leaflist,
          # Doesn't work, empty suggestions
          # suggestions=SchemaCompleter(path=self._get_ipv4_community_path,limit=5))
          # Doesn't work, exception 'not a node'
          # suggestions=KeyCompleter(path=self._get_ipv4_community_path,limit=5)
          ).add_boolean_argument('best',help='List only BEST routes')
           .add_boolean_argument('used',help='List only USED routes')
           .add_boolean_argument('valid',help='List only VALID routes')
           .add_boolean_argument('stale',help='List only STALE routes')
           )

    def get_data_schema(self):
        '''
            Return the Schema describing the data-model of the show routine.
            Think of this as the output of 'tree' - which is the data-model of the configuration.
        '''
        root = FixedSchemaRoot()

        route = root.add_child(
            'header',
            keys=['network-instance', 'community'],
            fields=['total path'],
        )
        route.add_child(
            'routes',
            keys=['Network', 'neighbor', 'path-id'],
            fields=[
                'received paths',
                'source neighbor',
                'community',
                'med',
                'status',
                'local-pref',
                'path-val',
                'ebgp',
                'next-hop',
                'path-count',
            ],
        )

        return root

    def print(self, state, arguments, output, **_kwargs):
        self._arguments = arguments
        self._requested_community = arguments.get('community', 'community')
        data_root = Data(arguments.schema)
        self._set_formatters(data_root)
        with output.stream_data(data_root):
            self._populate_data(data_root, state)

    def _populate_data(self, data_root, state):
        data_root.synchronizer.flush_fields(data_root)
        self._populate_route(state, data_root)
        data_root.synchronizer.flush_children(data_root.header)

    def _populate_route(self, state, data_root):
        netinst_name = self._arguments.get('network-instance', 'name')
        valid = self._arguments.get_or('valid', False)
        best = self._arguments.get_or('best', False)
        used = self._arguments.get_or('used', False)
        stale = self._arguments.get_or('stale', False)

        count = 0

        attr_sets = self._getAttrSets_(state)
        matching_attrset_ids = []
        for attr_set in attr_sets.get_descendants('/network-instance/bgp-rib/attr-sets/attr-set'):
            if self._matches_community(attr_set):
                logging.debug(f'Found matching attr_set: {attr_set.index}')
                matching_attrset_ids.append( int(attr_set.index) )

        result_header = data_root.header.create(netinst_name, self._requested_community)

        local_rib = self._getLocalRib_(state)
        for rib_route in local_rib.get_descendants('/network-instance/bgp-rib/afi-safi/ipv4-unicast/rib-in-out/rib-in-post/routes'):
            logging.debug(f'populate route starting for {rib_route.prefix}, {rib_route.neighbor}...')

            if int(rib_route.attr_id) not in matching_attrset_ids:
                logging.info(f'{rib_route.attr_id} not in {matching_attrset_ids}')
                continue

            if valid and not rib_route.valid_route:
                continue
            if best and not rib_route.best_route:
                continue
            if used and not rib_route.used_route:
                continue
            if stale and not rib_route.stale_route:
                continue

            result = result_header.routes.create(rib_route.prefix, rib_route.neighbor, rib_route.path_id)

            count += 1
            result.path_count = count
            result.status = self._set_status_code(rib_route)
            self._populate_route_attrs(state, result, netinst_name, rib_route.attr_id)
            result_header.total_path = count
            result.synchronizer.flush_fields(result)

            logging.debug(f'populate route ending for {rib_route.prefix}...')

    def _populate_route_advertisements(self, state, advertised, netinst_name, route_prefix):
        rib_out_path = build_path('/network-instance[name={name}]/bgp-rib/afi-safi[afi-safi-name=ipv4-unicast]/ipv4-unicast/rib-in-out/rib-out-post/routes[prefix={prefix}][neighbor=*][path-id=*]',
                                  name=netinst_name,
                                  prefix=route_prefix)
        rib_out_routes = state.server_data_store.get_data(rib_out_path, recursive=False)
        neighbors = ', '.join(str(rib_out_route.neighbor) for rib_out_route in rib_out_routes.get_descendants(
            '/network-instance/bgp-rib/afi-safi/ipv4-unicast/rib-in-out/rib-out-post/routes'))
        advertised.neighbors = neighbors

    def _populate_route_attrs(self, state, route_entry, netinst_name, attr_id):
        path = build_path('/network-instance[name={name}]/bgp-rib/attr-sets/attr-set[index={atr}]',
                          name=netinst_name, atr=str(attr_id))

        attrSets = state.server_data_store.stream_data(path, recursive=True)
        for attr in attrSets.get_descendants('/network-instance/bgp-rib/attr-sets/attr-set'):
            route_entry.local_pref = attr.local_pref
            route_entry.next_hop = attr.next_hop
            origin = self._get_origin(attr.origin)
            route_entry.med = attr.med or '-'
            route_entry.community = self._get_community(attr)
            as_path_str = ', '.join(str(as_path.member) for as_path in attr.as_path.get().segment.items())
            route_entry.path_val = origin + ' ' + as_path_str

    def _matches_community(self, attr):
        communities = attr.communities.get()
        return (self._requested_community in communities.community
            or self._requested_community in communities.ext_community
            or self._requested_community in communities.large_community)

    def _get_community(self, attr):
        community = []
        comms = attr.communities.get()
        community.append(', '.join(str(comm) for comm in comms.community))
        community.append(', '.join(str(comm) for comm in comms.ext_community))
        community.append(', '.join(str(comm) for comm in comms.large_community))
        return ', '.join(x for x in community if x)

    def _get_origin(self, origin):
        flag = ''
        if origin.startswith("igp"):
            flag = " i"
        if origin.startswith("egp"):
            flag = " e"
        if origin.startswith("incomplete"):
            flag = " ?"
        return flag

    def _set_status_code(self, route):
        status = '<'
        if route.best_route:
            status += 'Best,'
        if route.valid_route:
            status += 'Valid,'
        if route.used_route:
            status += 'Used,'
        if route.stale_route:
            status += 'Stale,'
        status += '>'
        return status

    def _getLocalRib_(self, state):
        '''
            Retrieve the BGP ipv4-unicast local-rib state.
        '''
        path = build_path('/network-instance[name={name}]/bgp-rib/afi-safi[afi-safi-name=ipv4-unicast]/ipv4-unicast/rib-in-out/rib-in-post/routes[prefix=*][neighbor=*][path-id=*]',
                          name=self._arguments.get('network-instance', 'name'),
                          )

        return state.server_data_store.stream_data(path, recursive=False)

    def _getAttrSets_(self, state):
        '''
            Retrieve the BGP attribute sets
        '''
        path = build_path('/network-instance[name={name}]/bgp-rib/attr-sets/attr-set',
                          name=self._arguments.get('network-instance', 'name'),
                          )

        return state.server_data_store.stream_data(path, recursive=True)


    def _set_formatters(self, data):
        '''
            Add the Formatter instances to the Data object.
            These formatters decide how the data is printed (using columns/key-value pairs, where to add borders, ...)
        '''
        data.set_formatter('/header', StatisticsFormatter_header())
        data.set_formatter('/header/routes', Indent(StatisticsFormatter_data(), indentation=2))
        # data.set_formatter('/header/advertised', StatisticsFormatter_footer())


class StatisticsFormatter_header(Formatter):

    def iter_format(self, entry, max_width):
        yield from self._format_header_line(max_width)
        yield f'Show report for the BGP routes with target community "{entry.community}" in network-instance "{entry.network_instance}"'
        yield from self._format_header(entry, max_width)
        # yield f'Network: {entry.prefix}'
        yield f'Matching Paths: {entry.total_path}'
        yield from entry.routes.iter_format(max_width)
        # yield from entry.advertised.iter_format(max_width)
        yield from self._format_header_line(max_width)

    def _format_header_line(self, width):
        return (
            data.print_line(width),
        )

    def _format_header(self, entry, width):
        return (
            data.print_line(width),
        )


class StatisticsFormatter_footer(Formatter):

    def iter_format(self, entry, max_width):
        yield f'Path {entry.path_num} was advertised to: '
        yield f'[ {entry.neighbors} ]'


class StatisticsFormatter_data(Formatter):
    def iter_format(self, entry, max_width):
        yield f'Path {entry.path_count}: {entry.network} {entry.status}'

        printer = TagValuePrinter(['Route source',
                                   'Route Preference',
                                   'BGP next-hop',
                                   'Path',
                                   'Communities',
                                   'RR Attributes',
                                   'Aggregation',
                                   'Unknown Attr',
                                   'Invalid Reason',
                                   'Tie Break Reason'],
                                  max_width=max_width)

        values = (
            self._get_route_source(entry),
            self._get_route_preference(entry),
            self._get_bgp_nexthop(entry),
            self._get_path(entry),
            self._get_communities(entry),
            self._get_rr_attr(entry),
            self._get_aggregation(entry),
            self._get_unknown_attr(entry),
            self._get_invalid_reason(entry),
            self._get_tie_break_reason(entry)
        )
        # values = (v for v in values)

        yield from data.indent(printer.iter_format(values), '  ')

    def _get_bgp_nexthop(self, entry):
        def _iter_chunks():
            if entry.next_hop:
                yield f'{entry.next_hop}'
        return ', '.join(_iter_chunks())

    def _get_path(self, entry):
        def _iter_chunks():
            if entry.path_val:
                yield f'{entry.path_val}'
        return ', '.join(_iter_chunks())

    def _get_communities(self, entry):
        def _iter_chunks():
            if entry.community:
                yield f'{entry.community}'
            else:
                yield f'None'
        return ', '.join(_iter_chunks())

    def _get_rr_attr(self, entry):
        return None

    def _get_aggregation(self, entry):
        return None

    def _get_unknown_attr(self, entry):
        return None

    def _get_invalid_reason(self, entry):
        return None

    def _get_tie_break_reason(self, entry):
        return None

    def _get_route_preference(self, entry):
        def _iter_chunks():
            if entry.med:
                yield f'MED is {entry.med}'
            else:
                yield f'No MED'
            if entry.local_pref:
                yield f'LocalPref is {entry.local_pref}'
            else:
                yield f'No LocalPref'

        return ', '.join(_iter_chunks())

    def _get_route_source(self, entry):
        def _iter_chunks():
            if entry.ebgp:
                yield f'External BGP'
            if entry.neighbor:
                yield f'neighbor {entry.neighbor}'
        return ', '.join(_iter_chunks())

    def _format_header(self, width):
        return (
            data.print_line(width),
            data.print_line(width),
        )
