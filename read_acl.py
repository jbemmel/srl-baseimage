#!/usr/bin/env python3

#
# Copyright(C) 2023 Nokia
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json

#
# A small Python script to read a JSON ACL file and assign the ipv4/6 policies to subinterfaces
#

def main():
    with open('/Projects/SRL_testing.srl_acl','r') as f:
        data = json.load(f)
        i = 0
        for filter in data:
            i += 1
            output = f"""
            /interface ethernet-1/1 subinterface {i} acl ipv4-filter input ['{filter['ipv4-filter']['name']}']
            """
            print( output )

if __name__ == "__main__":
    main()