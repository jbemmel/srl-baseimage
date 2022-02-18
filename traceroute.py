#!/usr/bin/python
###########################################################################
# Description:
#
# Copyright (c) 2018 Nokia
###########################################################################
from srlinux.mgmt.cli.cli_plugin import CliPlugin
from srlinux.mgmt.cli.execute_error import ExecuteError
from srlinux.mgmt.cli.plugins.bash_network_command_helper import execute_network_command, add_common_arguments
from srlinux.syntax import Syntax


class Plugin(CliPlugin):
    def load(self, cli, **_kwargs):
        syntax = Syntax('traceroute', help='Print the route packets trace to network host')
        add_tracert_arguments(syntax)
        cli.add_global_command(syntax, only_at_start_of_line=True, update_location=False, callback=send_traceroute)

        syntax6 = Syntax('traceroute6', help='Print the route packets trace to network host')
        add_tracert_arguments(syntax6)
        cli.add_global_command(syntax6, only_at_start_of_line=True, update_location=False, callback=send_traceroute)

        syntax_tcptraceroute = Syntax('tcptraceroute', help='tcptraceroute compatible wrapper for traceroute')
        add_tcptraceroute_arguments(syntax_tcptraceroute)
        cli.add_global_command(syntax_tcptraceroute, only_at_start_of_line=True, update_location=False,
                               callback=send_traceroute)


def send_traceroute(state, output, arguments, **_kwargs):
    if not state.is_interactive:
        raise ExecuteError(f"'{arguments}' is only supported in interactive mode")

    return execute_network_command(arguments.name, output, arguments)


def add_tracert_arguments(syntax):
    ''' Add the arguments shared between 'traceroute' and 'traceroute6' '''
    add_common_arguments(syntax)

    syntax.add_named_argument('-f', default=None, help='Specifies with what TTL to start. Defaults to 1')
    syntax.add_named_argument('-g', default=None, help='gateway : Route packets through the specified gateway')

    # JvB add source IP argument
    syntax.add_named_argument('-s', default=None, help='source : Use specified source IP')

    syntax.add_named_argument(
        '-p',
        default=None,
        help='port For ICMP tracing, specifies the initial ICMP sequence value (incremented by each probe too).')
    syntax.add_named_argument('-N', default=None, help='Specifies the number of probe packets sent out simultaneously.')
    syntax.add_named_argument(
        '-m',
        default=None,
        help='max_ttl Specifies the maximum number of hops (max time-to-live value) traceroute will probe.'
             ' The default is 30.')

    syntax.add_boolean_argument(
        '-A',
        help='Perform AS path lookups in routing registries and print results directly'
             ' after the corresponding addresses.')
    syntax.add_boolean_argument('-F', help='Do not fragment probe packets.')
    syntax.add_boolean_argument('-I', help='Use ICMP ECHO for probes')
    syntax.add_boolean_argument('-T', help='Use TCP SYN for probes')
    syntax.add_boolean_argument('-n', help='Do not try to map IP addresses to host names when displaying them.')


def add_tcptraceroute_arguments(syntax):
    add_common_arguments(syntax)

    syntax.add_named_argument('-w', default=None, help='Wait time')
    syntax.add_named_argument('-m', default=None, help='Max TTl')
