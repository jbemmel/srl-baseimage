###########################################################################
# Description:
#
# Copyright (c) 2018 Nokia
###########################################################################
import functools
import traceback
from typing import Optional, Union

from srlinux.mgmt.cli.cli_output import CliOutput
from srlinux.mgmt.cli.cli_state import CliState
from srlinux.mgmt.cli.command_node_with_arguments import CommandNodeWithArguments
from srlinux.mgmt.cli_engine.array_reader import ArrayReader
from srlinux.mgmt.cli_engine.command_executor import CommandsExecutor
from srlinux.mgmt.cli_engine.commands_reader import CommandsReader
from srlinux.mgmt.cli_engine.line_parser_auto_completer import LineParserAutoCompleter
from srlinux.mgmt.cli_engine.line_parser_auto_suggester import LineParserAutoSuggester
from srlinux.mgmt.cli_engine.line_parser import LineParser
from srlinux.mgmt.cli_engine.multiline_string_reader import MultilineStringReader
from srlinux.mgmt.cli_engine.space_auto_complete_decorator import SpaceAutoCompleteDecorator
from srlinux.mgmt.cli.execute_error import ExecuteError
from srlinux.mgmt.cli.global_state import get_global_state
from srlinux.mgmt.cli.idle_timer import get_idle_task
from srlinux.mgmt.cli.observer import ObserverGroup
from srlinux.mgmt.cli.parse_error import ParseError
from srlinux.mgmt.cli.session_termination import SessionTermination
from srlinux.mgmt.server.server_error import ServerError

# JvB added
import re
import os
from srlinux.location import build_path
from srlinux.schema.data_store import DataStore

try:
   from srlinux.strings import sanitize_name # Moved here in 21.6.3
except ImportError:
   from srlinux.data import utilities
   sanitize_name = utilities.sanitize_name

# For use with eval
import ipaddress

class CommandLoop(object):
    ''' Main executable class for any CLI engine.
        It will:
            - Read one line of input
            - Parse it into a list of 'Command's
            - Execute each of these 'Command's
            - Repeat until the input is empty

        Arguments:
           commands_reader: [type CommandsReader] Returns the input line-by-line
           line_parser: [type LineParser] Class responsible for parsing input-lines
           command_executor: [type CommandsExecutor] Class responsible for executing commands
           output: [type Output] Class where errors are printed
           stop_on_error: [type bool] If true execution stops after the first error
           observer: [type Observer] Optional observer that will be informed of each input line.
    '''

    def __init__(self,
                 commands_reader: CommandsReader,
                 line_parser: LineParser,
                 command_executor: CommandsExecutor,
                 output: CliOutput,
                 state: CliState,
                 observer: Optional[ObserverGroup] = None,
                 stop_on_error: bool = False):
        self._commands_reader = commands_reader
        self._input_reader = _add_decorators(commands_reader)
        self._line_parser = line_parser
        self._command_executor = command_executor
        self._state = state
        self._output = output
        self._stop_on_error = stop_on_error
        self._error_count = 0
        self._observer = observer or ObserverGroup()

    def loop(self) -> None:
        try:
            self._try_to_loop()
            if not self._state.is_switch_to_new_cli_engine_requested:
                self._observer.on_exit('quit was requested')
                # quitting via quit command, make sure the post lines still run
                # TODO(akocis): rework this to be more general and not rely on a specific function
                if hasattr(self._commands_reader, '_advance_to_next_reader'):
                    self._state._is_terminate_requested = False
                    try:
                        self._commands_reader._advance_to_next_reader()  # type: ignore[attr-defined]
                        self._try_to_loop()
                    finally:
                        self._state._is_terminate_requested = True
        except EOFError:
            # No more input lines
            self._observer.on_exit('Received EOF')
        except BrokenPipeError:
            # for example: sr_cli -- "show network-instance summary" | head
            self._observer.on_exit('Broken pipe')
            raise
        except Exception as e:
            # Catch unexpected exceptions, log them and reraise
            self._observer.on_exit(f'Uncaught exception {e}: {traceback.format_exc()}')
            raise

    def _try_to_loop(self) -> None:
        while not self._must_stop():
            self._process_line(self._next_input_line())
            get_idle_task().reset_idle_state()

    def _next_input_line(self) -> str:
        return self._input_reader.read_command(
            state=self._state,
            output=self._output,
            auto_completer=LineParserAutoCompleter(self._line_parser),
            auto_suggester=LineParserAutoSuggester(self._line_parser),
        )

    # JvB: added
    def _process_vars(self, line):

        def _lookup(match): # match looks like ${/path/x}
          _m = match[2:-1]  # Strip '${' and '}'

          # First check for NAME=VALUE env variable assignments
          env_var = re.match( "^([a-zA-Z0-9_]+)=(.*)$", _m )
          if env_var:
              _g = env_var.groups()
              if len(_g) == 2:
                self._output.print_warning_line( f'Set ENV {_g[0]}="{_g[1]}"' )
                # TODO could support lookup of state or config here, plus eval()
                self._env[ _g[0] ] = _g[1] # Could delete if empty
              else:
                self._output.print_warning_line( f'Group(s) mismatch? {_g}' )
              return ""

          _expr_eval = _m.split('|') # Support ${path|eval}, todo escaping
          _path_parts = _expr_eval[0].split('/')

          if len(_path_parts)>1:
             _leaf = _path_parts[-1]
             _la = _leaf.split('!!!')
             _root = '/'.join( _path_parts[0:-1] if len(_path_parts)>2 else ["",_la[0]] )
             self._output.print_warning_line( f'Lookup state path={match} _root={_root} parts={_path_parts}' )

             # Support lookup in state too, using '//'
             if _root[0:2] == "//":
               _root = _root[1:] # Strip '/'
               _path = build_path( _root )
               _store = self._state.server.get_data_store( DataStore.State )
               _data = _store.get_data(_path,recursive=False,include_field_defaults=True)

               # Test to set LLDP system description - nope, fails
               # _store.set_json( build_path('/system/lldp/system-description'), "JvB test" )

             else:
               _path = build_path( _root )
               _data = self._state.server_data_store.get_data(_path,recursive=False,include_field_defaults=True)

             _node = _data.get_first_descendant(_root)

             # Support annotations using '!!!' or '!!!key'
             if '!!!' in _leaf:
                 _anns = _node.get_annotations( _la[0] if len(_path_parts)>2 else None )
                 _result = _anns[0].text if _anns!=[] else ""
                 if _la[1]!='':
                    _kvs = _result.split(',')
                    _result = "" # If not found, return empty string
                    for k in _kvs:
                        _kv = k.split('=')
                        if len(_kv)==2 and _kv[0]==_la[1]:
                            self._output.print_warning_line( f'Using annotation {k}' )
                            _result = _kv[1]
                            break
             elif _node is not None:
                _result = getattr(_node,sanitize_name( _leaf ))
             else:
                _result = "" # For non-existent objects, resolve to empty string
             self._output.print_warning_line( f'root={_root} leaf={_leaf} -> {_result} type={type(_result)}' )
          else:
             _var = _path_parts[0]
             self._output.print_warning_line( f'Process ENV var={_var}' )
             if _var in self._env:
                 _result = self._env[ _var ]
             elif _var in os.environ:
                 _result = os.environ[ _var ]
             else:
                 _result = ""

          if len(_expr_eval) > 1:
              # Make result available as '_' in locals, and ipaddress
              _globals = { "ipaddress" : ipaddress }
              _locals  = { "_" : str( _result ) }
              return str( eval(_expr_eval[1], _globals, _locals ) )
          else:
              return str( _result ) # leaf value, can be int or bool

        # Make match non-greedy such that "${VAR}....${VAR2}" works correctly
        # Support nested references ${v1=${v2}} using recursive while loop
        while re.search( '\$\{([^$]*?)\}', line ):
           line = re.sub('\$\{([^$]*?)\}', lambda m: _lookup(m.group()), line)
        return line

    def _process_line(self, line: str) -> None:
        get_global_state().operation_terminated = False
        try:
            if self._state.is_session_terminated:
                raise SessionTermination('')

            self._state.check_for_remote_configuration_session_termination(self._output)
            line = self._process_vars(line) # JvB added
            self._observe_pre_parsing(line)

            self._state.parser_recursion_level = 0
            commands = self._line_parser.parse(line)
            self._observe_after_parsing(line, commands)

            result = self._execute_commands(commands, line)
            # result of None is considered success, same as result True
            if result is not None and (result is False or result is not True and result != 0):
                #  raise ExecuteError(f'Commands {commands} failed with return code = {result}')
                # only increase the counter (silent error)
                self._error_count = self._error_count + 1
                pass
        except ParseError as e:
            self._register_error(e.format())
        except ExecuteError as e:
            self._register_error(e.format())
        except ServerError as e:
            self._register_error(e.format())
        except KeyboardInterrupt:
            # Catches ctrl-c
            self._register_info("Command execution aborted : '{}'".format(line))
        except SessionTermination as e:
            self._register_error(e.format())
        except EOFError:
            # Catches ctrl-d
            # We silently ignore this.
            pass
        finally:
            # needed mainly for parsing failures
            self._state.perform_cleanup_routines(self._output)

    def _execute_commands(self, commands: CommandNodeWithArguments, line: str) -> Optional[Union[bool, int]]:
        try:
            return self._command_executor.execute(commands)
        finally:
            # The observer is always called, even if execution fails
            self._observe_after_executing(line, commands)

    def _register_error(self, error: str) -> None:
        self._error_count = self._error_count + 1
        self._output.print_error_line(error)
        self._observer.on_error(error)

    def _register_info(self, msg: str) -> None:
        self._output.print_info_line(msg)

    def _observe_after_parsing(self, line: str, commands: CommandNodeWithArguments) -> None:
        self._observer.after_parsing(state=self._state, input_line=line, commands=commands)

    def _observe_pre_parsing(self, line: str) -> None:
        self._observer.pre_parsing(state=self._state, input_line=line)

    def _observe_after_executing(self, line: str, commands: CommandNodeWithArguments) -> None:
        self._observer.after_executing(state=self._state, input_line=line, commands=commands)

    @property
    def error_count(self) -> int:
        ''' Number of parsing or execution errors encountered .'''
        return self._error_count

    def _must_stop(self) -> bool:
        if self.error_count and self._stop_on_error:
            return True
        return self._state.is_session_terminated


def _add_decorators(command_reader: CommandsReader) -> CommandsReader:
    '''
        Add the decorators that are allowed to transform the input lines before parsing it.

        Note that the decorators are applied top-to-bottom,
        so if we have decorators [A, B] we will return B(A(command_reader))
    '''
    decorators = [
        # If space completion is enabled, will expand all tokens that can uniquely be expanded.
        # e.g. will expand 'i abc s 1' into 'interface abc subinterface 1'.
        SpaceAutoCompleteDecorator,
        # If we encounter an unclosed string, keep reading until it is complete.
        # This allows the user to enter a multiline string, e.g.
        #     description "first
        #       second
        #       last"
        MultilineStringReader,
        # If we encounter an unclosed array, keep reading until it is complete.
        # This allows the user to enter an array on multiple lines, e.g.
        #     array [
        #       value
        #       other-value
        #    ]
        ArrayReader,
    ]

    return functools.reduce(
        lambda result, decorator: decorator(result),  # type: ignore[abstract]
        decorators,
        command_reader)
