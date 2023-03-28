#!/bin/bash
###########################################################################
# Description:
#     This script will launch the python script provided as first argument
#     in a virtual environment (forwarding any arguments passed to this script).
#
# Copyright (c) 2018-2023 Nokia
###########################################################################

_term (){
    echo "Caugth signal SIGTERM !! "
    kill -TERM "$child" 2>/dev/null
}

function main()
{
    trap _term SIGTERM
    local virtual_env="/opt/srlinux/python/virtual-env/bin/activate"
    local main_module="${1}"

    # source the virtual-environment, which is used to ensure the correct python
    # packages are installed, and the correct python version is used
    source "${virtual_env}"

    # Include local paths where custom packages are installed
    P1="/usr/local/lib/python3.6/site-packages"
    P2="/usr/local/lib64/python3.6/site-packages"
    NDK="/opt/rh/rh-python36/root/usr/lib/python3.6/site-packages/sdk_protos"
    # since 21.6
    SDK2="/usr/lib/python3.6/site-packages/sdk_protos"
    export PYTHONPATH="$P1:$P2:$NDK:$SDK2:$PYTHONPATH"

    # Pass all arguments beyond first
    python3 "${main_module}" "${@:2}" &

    child=$!
    wait "$child"
}

main "$@"
