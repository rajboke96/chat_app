# Server-side

import json
import socket, select
import traceback
import logging
logging.basicConfig(level=logging.DEBUG)

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
HEADER_SIZE=15

class SocketHelper:
    def send(conn, s):
        conn.send(s)

    def recv(conn, size=1024):
        if size < 1:
            return b''
        bdata = conn.recv(size)
        if bdata:
            return bdata
        else:
            raise ConnectionResetError(104, 'Connection reset by peer') 


class TCPAppServerAPI:
    PROTOCOL_NAME='TCPAppServerAPI'
    PROTOCOL_VERSION=1.0
    def gen_request(endpoint, args_dict={}, payload={}):
        logging.debug("Generating brequest packet")
        args=""
        for k, v in args_dict.items():
            args+=f"{k}={v},"
        args=args.strip(',')
        
        ctype = 'json'
        payload=json.dumps(payload)

        header = f"{TCPAppServerAPI.PROTOCOL_NAME}/{TCPAppServerAPI.PROTOCOL_VERSION},{ctype}".encode()
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
        logging.debug("Receiving cmd_args..")
        cmd_args=SocketHelper.recv(conn, cmd_args_size).decode()
        logging.debug(f"cmd_args: {cmd_args}")
        logging.debug("Receiving payload..")
        payload=SocketHelper.recv(conn, payload_size).decode()
        logging.debug(f"payload: {payload}")

        cmd, args=cmd_args.split('-')
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


class ChatServer:
    def __init__(self, host='127.0.0.1', port=65432, type='tcp', options=[]):
        self.host=host
        self.port=port
        logging.debug("Creating TCP Socket!")
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logging.debug("Setting socket options!")
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.rlist, self.wlist, self.elist = [self.server_sock], [], []
        self.connected_socks_dict={}

    def close_connection(self, conn):
        logging.debug(f"Closing connection: {conn.getpeername()}")
        self.connected_socks_dict.pop(f"{conn.getpeername()[0]}|{conn.getpeername()[1]}")
        conn.close()
        self.rlist.remove(conn)

    def list_socks(self, conn, request):
        logging.debug("Sending sockets list")
        payload={
            'data': [s.getpeername() if s!=self.server_sock else "server_sock" for s in self.rlist]
        }
        payload['data'].remove("server_sock")
        brequest = TCPAppServerAPI.gen_request('listsocks', {}, payload)
        SocketHelper.send(conn, brequest)
    
    def get_client_conn(self, ip, port):
        ckey=f"{ip}|{port}"
        conn=self.connected_socks_dict[ckey]
        return conn
            
    def forward_request(self,conn, request):
        logging.debug(f"Forwarding request: {request}")
        try:
            sock2=self.get_client_conn(request['arg_dict']['dst_ip'], request['arg_dict']['dst_port'])
        except KeyError as e:
            logging.debug(e)
            SocketHelper.send(conn, TCPAppServerAPI.gen_request('connect_unknown', request['arg_dict'], request['payload']))
            return
        logging.debug(f"Found client connection: {request['arg_dict']['dst_ip']}:{request['arg_dict']['dst_port']}")
        request['arg_dict']['src_ip']=conn.getpeername()[0]
        request['arg_dict']['src_port']=conn.getpeername()[1]
        logging.debug(f"Added source ip: {request['arg_dict']['src_ip']}, {request['arg_dict']['src_port']}")
        brequest=TCPAppServerAPI.gen_request(request['cmd'], request['arg_dict'], request['payload'])
        logging.debug(f"Forwarding request: {brequest}")
        SocketHelper.send(sock2, brequest)
            
    def process_request(self, conn, request):
        if request['cmd']=='listsocks':
            self.list_socks(conn, request)
        else:
            # Request forward to client
            self.forward_request(conn, request)
    def run(self):
        with self.server_sock:
            # Set the SO_REUSEADDR option
            logging.debug(f"Binding ip: {self.host}, port: {self.port}")
            self.server_sock.bind((self.host, self.port)) 
            self.server_sock.listen()
            logging.info(f"Socket listening on {self.host}:{self.port}")
            while 1:
                logging.debug("Waiting for new connection and client requests!")
                ready_rlist, ready_wlist, ready_elist = select.select(self.rlist, self.wlist, self.elist)
                logging.debug("Reading ready sockets!")
                for rsock in ready_rlist:
                    if rsock == self.server_sock:
                        # Accept new connection
                        client_conn, addr = rsock.accept()
                        self.rlist.append(client_conn)
                        self.connected_socks_dict[f"{addr[0]}|{addr[1]}"]=client_conn
                        logging.info(f"New client connected: {addr}")
                    else:
                        logging.info(f"Handling client request!")
                        try:
                            # Handle client Requests
                            request = TCPAppServerAPI.receive_request(rsock)
                            self.process_request(rsock, request)
                        except (ConnectionResetError, OSError) as e:
                            logging.error(f"{rsock.getpeername()} closed connection!: {e}")
                            self.close_connection(rsock)
                        except Exception as e:
                            logging.error(e)
                            traceback.print_exc()
                            response = TCPAppServerAPI.gen_request('',{},"Error")
                            SocketHelper.send(rsock, response)
                            self.close_connection(rsock)
                            
chat_server = ChatServer()
chat_server.run()