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