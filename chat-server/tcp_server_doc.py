# Define a chat server

# requirement
# 1. multiple clients should able to connect to a server.
# 2. connected clients should see other connected clients.
# 3. client should able to talk another client.

# Add Chat Protocol
"""
    connect 127.0.0.1 52038
    --> Reponse format

    0802300012fast-chat/1.0,texthello world!

    --> Request format

    0802300012fast-chat/1.0,textsend_msg,ip=127.0.0.1,port=22311hello world!

    0802300000,textsend_msgip=127.0.0.1,port=22311hello world!

    command_size,arg_size,payload_size-main_request 
    
    1. take header with fixed size
    2. fetch header and extract command_size arg_size payload_size info.
    3. one-by-one fetch 3 of them

    args_list payload
    show_online_socks
    send_msg ip:port content

    --> Response format
    1. take header with fixed size
    2. status:status_message payload_size
"""

# c1 msg to c2

# c1 cli
# connect c2_ip:c2_port
# connect_req (blocking)
    # connect_req_cancel
    # connect_wait(ip, port, status)
    # connect_ack

# after connect_req client waits for connect_ack
# what to do when client waits?
    # after connect_req sent. ask user to that connecting do you want to abort?
    # if client sends connect_ack then do connect_ack
    # if client sends connect_wait then do connect_wait