"""Grab one connected Guild Wars client, read one context, print its data."""

import py4gw

client = py4gw.connect(py4gw.win32.list_processes()[0])

print(client.pid)
print(py4gw.context.charcontext.get())

py4gw.disconnect()
