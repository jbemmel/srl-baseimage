#!/usr/bin/python
###########################################################################
# Description:
#
# Copyright (c) 2018 Nokia
###########################################################################
from srlinux import strings
from srlinux.data import ColumnFormatter, Data, Alignment, Formatter, print_line
from srlinux.data.utilities import Percentage
from srlinux.location import build_path
from srlinux.mgmt.cli.cli_plugin import CliPlugin
from srlinux.mgmt.cli.key_completer import KeyCompleter
from srlinux.schema import FixedSchemaRoot
from srlinux.syntax import Syntax


class Plugin(CliPlugin):
    __slots__ = (
        '_total_entries',
        '_static_entries',
        '_dynamic_entries',
    )

    def load(self, cli, **_kwargs):
        arpnd = cli.show_mode.add_command(Syntax('arpnd'))

        arpnd.add_command(
            (Syntax('neighbors', help='Show IPv6 neighbors report')
             .add_named_argument('interface', default='*', suggestions=KeyCompleter(path=self._interface_path))
             .add_named_argument('subinterface', default='*', suggestions=KeyCompleter(path=self._subinterface_path))
             .add_named_argument('ipv6-address', default='*',
                                 suggestions=KeyCompleter(path=lambda arguments: self._ipv6_address_path(arguments)))
             ),
            update_location=False,
            callback=self._print,
            schema=self._get_my_schema(False),
        )

        arpnd.add_command(
            (Syntax('arp-entries', help='Show IPv4 arp entries report')
             .add_named_argument('interface', default='*', suggestions=KeyCompleter(path=self._interface_path))
             .add_named_argument('subinterface', default='*', suggestions=KeyCompleter(path=self._subinterface_path))
             .add_named_argument('ipv4-address', default='*',
                                 suggestions=KeyCompleter(path=lambda arguments: self._ipv4_address_path(arguments)))
             ),
            update_location=False,
            callback=self._print,
            schema=self._get_my_schema(True),
        )

        arpnd.add_command(
            Syntax('capacity', help='Show summary of ARP/ND entries in use out of total available'),
            update_location=False,
            callback=self._print_capacity,
            schema=self._get_my_schema(v4=True,summaryOnly=True),
        )

    def _get_my_schema(self, v4, summaryOnly=False):
        root = FixedSchemaRoot()

        # Put totals at top
        root.add_child('summary', fields=['Total entries', 'Static entries', 'Dynamic entries'])

        if summaryOnly:
            root.add_child('capacity', fields=['Used percentage', 'Used entries', 'Free entries'])
        else:
            root.add_child('neighbor',
                           keys=['Interface', 'Subinterface', 'Neighbor'],
                           fields=[
                               'Origin',
                               'Link layer address',
                               'Expiry'] if v4 else [
                               'Origin',
                               'Link layer address',
                               'Current state',
                               'Next state change',
                               'Is Router']
                          )
        return root

    def _interface_path(self, arguments):
        return build_path('/interface[name=*]')

    def _subinterface_path(self, arguments):
        return build_path(
            '/interface[name={name}]/subinterface[index=*]',
            name=arguments.get('interface'))

    def _ipv4_address_path(self, arguments, wildcard=True):
        return build_path(
            '/interface[name={name}]/subinterface[index={index}]/ipv4/arp/neighbor[ipv4-address={address}]',
            name=arguments.get('interface'),
            index=arguments.get('subinterface'),
            address='*' if wildcard else arguments.get('ipv4-address')
        )

    def _ipv6_address_path(self, arguments, wildcard=True):
        return build_path(
            '/interface[name={name}]/subinterface[index={index}]/ipv6/neighbor-discovery/neighbor[ipv6-address={address}]',
            name=arguments.get('interface'),
            index=arguments.get('subinterface'),
            address='*' if wildcard else arguments.get('ipv6-address')
        )

    # info from state /platform linecard 1 forwarding-complex 0 datapath xdp resource arp-nd-entries | as json
    def _arp_nd_entries_path(self):
        return build_path(
            '/platform/linecard[slot=*]/forwarding-complex[name=*]/datapath/xdp/resource[name=arp-nd-entries]',
        )
        #resource arp-nd-entries {
        #    used-percent 0
        #    used-entries 9
        #    free-entries 16374

    def _fetch_state(self, state, arguments, v4):
        path = self._ipv4_address_path(
            arguments, False) if v4 else self._ipv6_address_path(arguments, False)

        return state.server_data_store.stream_data(path, recursive=True)

    def _init_members(self):
        self._total_entries = 0
        self._static_entries = 0
        self._dynamic_entries = 0

    def _populate_data(self, data, server_data, v4):
        self._init_members()
        data.synchronizer.flush_fields(data)

        for interface in server_data.interface.items():
            self._add_subinterface(data, interface.name,
                                   interface.subinterface, v4)

        data.synchronizer.flush_children(data.neighbor)

        summ = data.summary.create()
        summ.total_entries = self._total_entries
        summ.static_entries = self._static_entries
        summ.dynamic_entries = self._dynamic_entries
        summ.synchronizer.flush_fields(summ)

        data.synchronizer.flush_children(data.summary)

        return data

    def _populate_cap_data(self, data, server_data):
        data.synchronizer.flush_fields(data)
        for i in server_data.platform.get().linecard.items():
         for c in i.forwarding_complex.items():
          for x in c.datapath.get().xdp.get().resource.items():
            # TODO average or collect all
            # XXX doesn't actually work, unclear why. Complains about field mismatch
            self._used_percent = x.get_field('used_percentage') or '-'
            self._used_entries = x.get_field('used_entries') or '-'
            self._free_entries = x.get_field('free_entries') or '-'

        cap = data.capacity.create()
        cap.used_percent = self._used_percent
        cap.used_entries = self._used_entries
        cap.free_entries = self._free_entries
        cap.synchronizer.flush_fields(cap)
        data.synchronizer.flush_children(data.capacity)

        return data

    def _add_subinterface(self, data, interface_name, server_data, v4):
        # server_data is an instance of DataChildrenOfType

        for subinterface in server_data.items():
            self._add_neighbor(data, interface_name, subinterface.index,
                               subinterface.ipv4.get().arp.get().neighbor if v4
                               else subinterface.ipv6.get().neighbor_discovery.get().neighbor, v4)

    def _add_neighbor(self, data, interface_name, subinterface_index, server_data, v4):
        for neighbor in server_data.items():
            child = data.neighbor.create(
                interface_name, subinterface_index, neighbor.ipv4_address if v4 else neighbor.ipv6_address)

            self._total_entries += 1
            child.origin = neighbor.origin
            if neighbor.origin == 'static':
                self._static_entries += 1
            else:
                self._dynamic_entries += 1
            child.link_layer_address = neighbor.link_layer_address
            expiration_time = neighbor.expiration_time if v4 else neighbor.next_state_time
            time_remaining = strings.natural_relative_time(
                expiration_time) if expiration_time else None
            if v4:
                child.expiry = time_remaining
            else:
                child.next_state_change = time_remaining
                child.current_state = neighbor.current_state
                child.is_router = neighbor.is_router
            child.synchronizer.flush_fields(child)

    def _set_formatters(self, data, v4):
        ip_length = 15 if v4 else 39
        column_widths = [
            Percentage(10),
            Percentage(10),
            ip_length,
            Percentage(10),
            Percentage(20),
        ]
        if v4:
            column_widths.append(Percentage(40))
        else:
            column_widths.append(Percentage(10))
            column_widths.append(Percentage(20))
            column_widths.append(Percentage(10))

        data.set_formatter('/neighbor',
                           ColumnFormatter(ancestor_keys=True,
                                           widths=column_widths,
                                           horizontal_alignment={
                                               'Subinterface': Alignment.Right,
                                               'Neighbor': Alignment.Right,
                                               'Origin': Alignment.Right
                                           }
                                           )
                           )
        data.set_formatter('/summary', SummaryFormatter())

    def _ipv4_variant(self, arguments):
        return arguments.node.name == 'arp-entries'

    def _print(self, state, arguments, output, **_kwargs):
        v4 = self._ipv4_variant(arguments)
        server_data = self._fetch_state(state, arguments, v4)
        result = Data(arguments.schema)
        self._set_formatters(result, v4)

        with output.stream_data(result):
            self._populate_data(result, server_data, v4)

    def _print_capacity(self, state, arguments, output, **_kwargs):
        path = self._arp_nd_entries_path()
        server_data = state.server_data_store.stream_data(path, recursive=True)
        result = Data(arguments.schema)
        result.set_formatter('/capacity', CapacityFormatter())

        with output.stream_data(result):
            self._populate_cap_data(result, server_data)


class SummaryFormatter(Formatter):

    def iter_format(self, entry, max_width):
        yield print_line(max_width, '-')
        yield from self._format_entry(entry, max_width)
        yield print_line(max_width, '-')

    def _format_entry(self, entry, max_width):
        yield f'  Total entries : {entry.total_entries} ({entry.static_entries} static, {entry.dynamic_entries} dynamic)'

class CapacityFormatter(Formatter):

    def iter_format(self, entry, max_width):
        yield print_line(max_width, '-')
        yield from self._format_entry(entry, max_width)
        yield print_line(max_width, '-')

    def _format_entry(self, entry, max_width):
        yield f'  Used entries : {entry.used_entries}({entry.used_percent}%) Free entries : {entry.free_entries}'
