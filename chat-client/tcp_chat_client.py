# Client-side
import sys
import json
import time
import socket, select

import logging
logging.basicConfig(level=logging.ERROR)

from tcp_client_server_api import TCPClientServerApi
from socket_helper import SocketHelper

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432        # The port used by the server

# Socket Wrapper class

# tcp protocol for communication between client and server
# client

# chatclient 
# give cli interface for user to interact
# show list of available clients
# request to connect to any one of client and start chatting

class ConnectedClient:
    def __init__(self):
        self._status=None
        self.ip=None
        self.port=None
        self.connect_callbacks={}
    @property
    def status(self):
        return self._status
    @status.setter
    def status(self, value):
        self._status=value
        self.connect_callbacks[value]['callback'](*self.connect_callbacks['connecting']['args'])
    def register_callback_for(self, status, callback, *callback_args):
        self.connect_callbacks[status] = {'callback': callback, 'args': callback_args}

class ChatClient:
    def __init__(self, server_ip, server_port, type='tcp', options=[]):
        self.server_ip = server_ip
        self.server_port = server_port
        self.type=type
        self.options=options

        logging.debug("Creating TCP Socket!")
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.rlist, self.wlist, self.elist = [sys.stdin, self.client_sock], [] , []

        self.connected_client = None

        self.prompt_sym=">"
        self.default_prompt=f"Server{self.prompt_sym}"
        self.prompt = self.default_prompt

        self.select_timeout = None
        self.connected_client = ConnectedClient()
        self.connected_client.register_callback_for(None, self.reset_callback, self.connected_client)
        self.connected_client.register_callback_for('connecting', self.connected_callback, self.connected_client)
        self.connected_client.register_callback_for('wait', self.wait_callback, self.connected_client)
        self.connected_client.register_callback_for('connected', self.connected_callback, self.connected_client)
    
    def reset_callback(self, connected_client):
        if sys.stdin not in self.rlist:
            self.rlist.append(sys.stdin)
        self.prompt=self.default_prompt
        self.select_timeout=None

    def connecting_callback(self, connected_client):
        if sys.stdin in self.rlist:
            self.rlist.remove(sys.stdin)
        self.prompt=f"{self.default_prompt}"
        self.select_timeout=10
    def wait_callback(self, connected_client):
        if sys.stdin in self.rlist:
            self.rlist.remove(sys.stdin)
        self.prompt=f"{self.default_prompt}"
    def connected_callback(self, connected_client):
        if sys.stdin not in self.rlist:
            self.rlist.append(sys.stdin)
        self.prompt=f"{connected_client.ip}:{connected_client.port}{self.prompt_sym}"
        self.select_timeout=None
    def is_client_on_connect(self, ip, port):
        return self.connected_client.status and f"{self.connected_client.ip}{self.connected_client.port}" == f"{ip}{port}"
    def is_client_connected(self, ip, port):
        return self.connected_client.status=='connected' and f"{self.connected_client.ip}{self.connected_client.port}" == f"{ip}{port}"
    def send_connect_ack(self, request, dst_ip, dst_port):
        logging.debug("Sending connect_ack packet!")
        brequest = TCPClientServerAPI.gen_request
        ('connect_ack', {'dst_ip': dst_ip, 'dst_port': dst_port})
        logging.debug(f"Created connect_ack packet: {brequest}")
        SocketHelper.send(self.client_sock, brequest)
        logging.debug(f"connect_ack packet sent {dst_ip}:{dst_port}!")
    
    def handle_connect_ack(self, request, src_ip, src_port):
        logging.debug("Handling connect_ack packet!")
        logging.debug(f"Handling connect_ack from {src_ip}:{src_port}")
        if self.connected_client.status:
            if not self.is_client_on_connect(src_ip, src_port):
                logging.debug(f"Already connected to {self.connected_client}")
                self.send_connect_wait(src_ip, src_port)
            else:
                logging.debug("No client is connected currently! Accepting connect_ack request")
                self.connected_client.ip=src_ip
                self.connected_client.port=src_port
                self.connected_client.status='connected'
                print("Client connected!")
            
    def send_connect_wait(self, dst_ip, dst_port):
        logging.debug("Sending connect_wait packet!")
        brequest = TCPClientServerAPI.gen_request('connect_wait', {'dst_ip': dst_ip, 'dst_port': dst_port})
        logging.debug(f"Created connect_wait packet: {brequest}")
        SocketHelper.send(self.client_sock, brequest)
        logging.debug(f"connect_wait packet sent {dst_ip}:{dst_port}!")

    def handle_connect_wait(self, request, dst_ip, dst_port):
        logging.debug("Handling connect_wait packet!")
        if self.connected_client.status:
            if self.is_client_on_connect(dst_ip, dst_port):
                self.connected_client.status='wait'
                print("Client Busy!")
    
    def send_connect_unknown(self, request, dst_ip, dst_port):
        args_dict={'dst_ip': dst_ip, 'dst_port': dst_port}
        brequest=TCPClientServerAPI.gen_request('connect_unknown', args_dict, '')
        logging.debug(f"Created connect_unknown packet: {brequest}")
        SocketHelper.send(self.client_sock, brequest)
        logging.debug(f"connect_unknown packet sent {dst_ip}:{dst_port}!")

    def handle_connect_unknown(self, request, dst_ip, dst_port):
        logging.error(f"Invalid {dst_ip}:{dst_port}")
        if self.is_client_on_connect(dst_ip, dst_port):
            self.connected_client.status=None
            self.connected_client.ip=None
            self.connected_client.port=None
            print(f"Client unavailable!")

    def send_connect_req(self, dst_ip, dst_port):
        print("Press ctrl+c to abort connect")
        logging.debug(f"Connecting to :{dst_ip}:{dst_port}")
        self.connected_client.status='connecting'
        self.connected_client.ip=dst_ip
        self.connected_client.port=dst_port
        brequest = TCPAppServerAPI.gen_request('connect_req', {'dst_ip': dst_ip, 'dst_port': dst_port})
        logging.debug(f"Created connect_req packet: {brequest}")
        SocketHelper.send(self.client_sock, brequest)
        logging.debug(f"connect_req packet sent {dst_ip}:{dst_port}!")

    def send_connect_abort(self, dst_ip, dst_port):
        logging.debug(f"Sending connect_abort to :{dst_ip}:{dst_port}")
        self.connected_client.status=None
        self.connected_client.ip=dst_ip
        self.connected_client.port=dst_port
        brequest = TCPClientServerAPI.gen_request('connect_abort', {'dst_ip': dst_ip, 'dst_port': dst_port})
        logging.debug(f"Created connect_abort packet: {brequest}")
        SocketHelper.send(self.client_sock, brequest)
        logging.debug(f"connect_abort packet sent {dst_ip}:{dst_port}!")

    def handle_connect_abort(self, request, dst_ip, dst_port):
        if self.is_client_on_connect(dst_ip, dst_port):
            self.connected_client.status=None
            self.connected_client.ip=None
            self.connected_client.port=None
            print(f"Connection aborted!")

    def handle_connect_req_cancel(self, request, dst_ip, dst_port):
        if self.is_client_on_connect(dst_ip, dst_port):
            self.connected_client.status=None
            self.connected_client.ip=None
            self.connected_client.port=None
            print("Connect declined!")
    def handle_send_msg(self, request, dst_ip, dst_port):
        print('\n', request['payload'])
    def handle_listsocks(self, request):
        logging.debug(type(request['payload']))
        for s in request['payload']['data']:
            if f"{s[0]}:{s[1]}" == f"{self.client_sock.getsockname()[0]}:{self.client_sock.getsockname()[1]}":
                print(f"You - {s}")
            else:
                print(f"Client - {s}")
    def handle_connect_req(self, request, dst_ip, dst_port):
        logging.debug(f"Connection request from: {dst_ip}:{dst_port}")
        if self.connected_client.status:
            if f"{self.connected_client.ip}{self.connected_client.port}" != f"{dst_ip}{dst_port}":
                logging.debug(f"Already connected to {self.connected_client}")
                self.send_connect_wait(dst_ip, dst_port)
            else:
                pass # ignore connect_wait packet
        else:
            print(f"Do you want to accept a connect from {dst_ip}:{dst_port}? (y/n)")
            res = input()
            if 'y'==res.lower().strip('\n'):
                logging.debug("No client is connected currently! Accepting connect_ack request")
                self.connected_client.ip=dst_ip
                self.connected_client.port=dst_port
                self.connected_client.status='connected'

                brequest = TCPClientServerAPI.gen_request('connect_ack', {'dst_ip': dst_ip, 'dst_port': dst_port})
                logging.debug(f"Created connect_ack packet: {brequest}")
                SocketHelper.send(self.client_sock, brequest)
                logging.debug(f"connect_ack packet sent {dst_ip}:{dst_port}!")
                print("Connect accepted!")
            else:
                brequest = TCPClientServerAPI.gen_request('connect_req_cancel', {'dst_ip': dst_ip, 'dst_port': dst_port})
                logging.debug(f"Created connect_req_cancel packet: {brequest}")
                SocketHelper.send(self.client_sock, brequest)
                logging.debug(f"connect_req_cancel packet sent {dst_ip}:{dst_port}!")
                print("Connect declined!")
                
    def send_msg(self, dst_ip, dst_port):
        args_dict={'dst_ip': dst_ip, 'dst_port': dst_port}
        brequest=TCPClientServerAPI.gen_request('send_msg', args_dict, '')
        logging.debug(f"Created send_msg packet: {brequest}")
        SocketHelper.send(self.client_sock, brequest)
        logging.debug(f"send_msg packet sent {dst_ip}:{dst_port}!")

    def send_reconnect_req(self, dst_ip, dst_port):
        logging.debug("Trying to reach!")
        print("Busy client: ", dst_ip, dst_port)
        print("Do you want to wait? (y/n)")
        res = input()
        if 'n'==res.lower().strip('\n'):
            self.connected_client.ip=None
            self.connected_client.port=None
            self.connected_client.status=None
        else:
            brequest = TCPClientServerAPI.gen_request('connect_req', {'dst_ip': dst_ip, 'dst_port': dst_port})
            logging.debug(f"Created connect_req packet: {brequest}")
            SocketHelper.send(self.client_sock, brequest)
            logging.debug(f"connect_req packet sent {dst_ip}:{dst_port}!")

    def process_input(self, s):
        logging.debug(f"Processing input: {s}")
        if self.connected_client.status:
            logging.debug(f"Client {self.connected_client.ip}:{self.connected_client.port} connected!")
            args_dict={'dst_ip': self.connected_client.ip, 'dst_port': self.connected_client.port}
            brequest=TCPClientServerAPI.gen_request('send_msg', args_dict, s)
            SocketHelper.send(self.client_sock, brequest)
        else:
            cmd_list = s.split(" ")
            logging.debug(f"cmd_list: {cmd_list}")
            if cmd_list[0] == 'connect':
                if len(cmd_list) == 2:
                    self.send_connect_req('127.0.0.1', cmd_list[1])
                else:
                    self.send_connect_req(cmd_list[1], cmd_list[2])
            elif cmd_list[0] == 'listsocks':
                request = TCPClientServerAPI.gen_request('listsocks')
                SocketHelper.send(self.client_sock, request)
    
    def process_request(self, request):
        if request['cmd']=='listsocks':
                self.handle_listsocks(request)
        elif request['cmd']=='connect_unknown':
            src_ip = request['arg_dict']['dst_ip']
            src_port=request['arg_dict']['dst_port']
        else:
            src_ip = request['arg_dict']['src_ip']
            src_port=request['arg_dict']['src_port']
        if request['cmd']=='send_msg':
            self.handle_send_msg(request, src_ip, src_port)
        else:
            if request['cmd'] == 'connect_wait':
                self.handle_connect_wait(request, src_ip, src_port)
            elif request['cmd']=='connect_req':
                self.handle_connect_req(request, src_ip, src_port)
            elif request['cmd']=='connect_req_cancel':
                self.handle_connect_req_cancel(request, src_ip, src_port)
            elif request['cmd']=='connect_ack':
                self.handle_connect_ack(request, src_ip, src_port)
            elif request['cmd']=='connect_unknown':
                self.handle_connect_unknown(request, src_ip, src_port)
            elif request['cmd']=='connect_abort':
                self.handle_connect_abort(request, src_ip, src_port)

    def run(self):
        logging.debug(f"Connecting to server: {self.server_ip}:{self.server_port}")
        self.client_sock.connect((self.server_ip, self.server_port))
        logging.debug("Connected!")
        while 1:
            try:
                if self.connected_client.status and (self.connected_client.status == 'connecting' or self.connected_client.status == 'wait'):
                    pass
                else:
                    print(self.prompt, end=' ', flush=True)
                logging.debug("Waiting for user input and server messages!")
                ready_rlist, ready_wlist, ready_elist = select.select(self.rlist, self.wlist, self.elist, self.select_timeout)
                logging.debug("Checking if any connected client")
                
                logging.debug("Reading ready sockets!")
                for r_fd in ready_rlist:
                    if r_fd == sys.stdin:
                        logging.debug("Reading user input!")
                        payload = r_fd.readline().strip('\n')
                        if not payload:
                            continue
                        self.process_input(payload)
                    else:
                        logging.info(f"Handling server request!")
                        # receive socket message
                        request = TCPClientServerAPI.receive_request(self.client_sock)
                        self.process_request(request)
                # if self.connected_client.status and (self.connected_client.status == 'connecting' or self.connected_client.status == 'wait'):
                #     self.send_reconnect_req(self.connected_client.ip, self.connected_client.port)
                logging.debug(f"rlist len: {len(ready_rlist)}")        
                logging.debug("loop end.....")
            except KeyboardInterrupt:
                if self.connected_client.status:
                    self.send_connect_abort(self.connected_client.ip, self.connected_client.port)
                    print("Connection aborted!")
                else:
                    raise KeyboardInterrupt()


client = ChatClient('127.0.0.1', 7000)
client.run()
