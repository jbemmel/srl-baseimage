#!/usr/bin/env python3

#
# Copyright(C) 2023 Nokia
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#
# A regular Python script that gets called from the event handler proxy script
# via run-python-script.sh
#

import json
import sys

# this would not work in micropython...
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

args = sys.argv[1:]

#   python3 splunk_notify.py --json '<json string>'
if len(args) == 2 and args[0] == '--json':
    in_json = json.loads(args[1])
    print( json.dumps(in_json,indent=2) )

    paths = in_json["paths"]
    options = in_json["options"]

    debug = options.get("debug") == "true"

    token = options.get("token")
    channel = options.get("channel")
    client = WebClient(token=token)

    client.chat_postMessage(channel=channel, text="Uh oh! BGP trouble...")
    print( "Splunk message sent!" )
    sys.exit(0)

sys.exit(-1)
