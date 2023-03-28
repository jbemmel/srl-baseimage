# Configure DNS
set /system dns network-instance mgmt server-list [ 1.1.1.1 8.8.8.8 8.8.4.4 ]

# Configure Splunk script
# /system event-handler instance splunk_alert
# admin-state enable
# upython-script eh_proxy2python.py
# paths [
#  "network-instance default protocols bgp neighbor * last-event"
# ]
# options
#  object debug { value true }
#  object python-script { value "/opt/splunk_notify/splunk_notify.py" }
#  object token { value "xxx" }
#  object channel { value "#general" }
