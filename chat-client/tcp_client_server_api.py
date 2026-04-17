class TCPClientServerAPI:
    PROTOCOL_NAME='TCPClientServerAPI'
    PROTOCOL_VERSION=1.0
    def gen_request(endpoint, args_dict={}, payload=''):
        logging.debug("Generating brequest packet")
        args=""
        for k, v in args_dict.items():
            args+=f"{k}={v},"
        args=args.strip(',')

        ctype = 'json'

        header = f"{TCPClientServerAPI.PROTOCOL_NAME}/{TCPClientServerAPI.PROTOCOL_VERSION},{ctype}".encode()
        header_size = len(header).to_bytes(1, 'big')

        cmd_args=f"{endpoint}-{args}".encode()
        cmd_args_size = len(cmd_args).to_bytes(2, 'big')

        payload=f"{payload}".encode()
        payload_size = len(payload).to_bytes(2, 'big')

        brequest = header_size+cmd_args_size+payload_size+header+cmd_args+payload
        logging.debug(f"brequest packet: {brequest}")
        return brequest

    def receive_request(conn):
        logging.debug(f"Receiving request from: {conn.getpeername()}")
        header_size = int.from_bytes(SocketHelper.recv(conn, 1), byteorder='big')
        cmd_args_size = int.from_bytes(SocketHelper.recv(conn, 2), byteorder='big')
        payload_size = int.from_bytes(SocketHelper.recv(conn, 2), byteorder='big')
        logging.debug(f"header_size: {header_size}, cmd_args_size: {cmd_args_size}, payload_size: {payload_size}")
        logging.debug("Receiving header..")
        header = SocketHelper.recv(conn, header_size).decode()
        logging.debug(f"header: {header}")
        logging.debug(header.split(','))
        _, ctype = header.split(',')
        logging.debug("Receiving cmd_args..")
        cmd_args=SocketHelper.recv(conn, cmd_args_size).decode()
        logging.debug(f"cmd_args: {cmd_args}")
        logging.debug("Receiving payload..")
        payload=SocketHelper.recv(conn, payload_size).decode()
        d={}
        logging.debug(payload)
        if ctype=='json':
            payload=json.loads(payload)
        logging.debug(f"cmd_args.split: {cmd_args.split('-')}")
        cmd_args_split=cmd_args.split('-')
        cmd, args=cmd_args_split[0], cmd_args_split[1]
        logging.debug(f"cmd: {cmd}")
        logging.debug(f"args: {args}")
        arg_dict={}
        if args:
            for arg in args.split(','):
                k, v = arg.split('=')
                arg_dict[k]=v
        request={
            'cmd': cmd,
            'arg_dict': arg_dict,
            'payload': payload
        }
        logging.debug(f"Request object: {request}")
        return request