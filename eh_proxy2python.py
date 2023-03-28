#
# Copyright(C) 2023 Nokia
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#
# A Micropython Event Handler script that proxies to a "normal" script (Python or other)
#
# Example config:
EXAMPLE_CONFIG = """
enter candidate
/system event-handler instance splunk_alert
admin-state enable
upython-script eh_proxy2python.py
paths [
 "network-instance default protocols bgp neighbor * last-event"
]
options {
 object debug { value true }
 object python-script { value "/opt/splunk_notify/splunk_notify.py" }
 object token { value "xxx" }
 object channel { value "some_splunk_channel_id" }
}
commit stay
"""
import json

# main entry function for event handler
def event_handler_main(in_json_str):

    # parse input json string passed by event handler, to get python-script
    in_json = json.loads(in_json_str)
    # paths = in_json["paths"]
    options = in_json["options"]
    # data = in_json["persistent-data"] if "persistent-data" in in_json else {}

    if options.get("debug") == "true":
       print( in_json_str )

    python_script = options.get("python-script")

    response_actions = [ {
        "run-script": { # runs as 'admin' user in /home/admin
            "cmdline": "/opt/run-python-script.sh " + python_script + " --json '" + in_json_str + "'"
        }
    } ] if python_script else []
    response = { "actions": response_actions }
    return json.dumps(response)
