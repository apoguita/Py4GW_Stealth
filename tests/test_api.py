import py4gw

clients = py4gw.win32.list_processes()
selected_client = clients[0]

py4gw.connect(selected_client)

char_context = py4gw.context.charcontext.get()
if char_context is not None:
    print(char_context.player_name_str or "in selection menus")    


py4gw.disconnect()