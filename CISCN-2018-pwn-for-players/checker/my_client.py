import uuid
import socket
import struct
import codecs

DEBUG = False
if DEBUG:
    send = socket.socket.send
    def send_debug(self, send_str):
        print('sending %s' % codecs.encode(send_str, 'hex'))
        return send(self, send_str)
    socket.socket.send = send_debug

    recv = socket.socket.recv
    def recv_debug(self, recv_len):
        recved = recv(self, recv_len)
        print('receiving %s' % codecs.encode(recved, 'hex'))
        return recved
    socket.socket.recv = recv_debug

def p32(num):
    return struct.pack('>I', num)

def p64(num):
    return struct.pack('>Q', num)

def u32(num_byte):
    return struct.unpack('>I', num_byte)[0]

def u64(num_byte):
    return struct.unpack('>Q', num_byte)[0]


SERVICE_PORT = 1337
MAGIC_SEND = b'RPCM'
MAGIC_RECV = B'RPCN'

class RpcConnectionException(Exception):
    pass


class RpcPacket(object):
    def __init__(self):
        self.magic = MAGIC_SEND
        self.packet_type = p32(0)
        self.length = 12

    def into(self):
        return self.magic + p32(self.length) + self.packet_type


# Requests
class RpcConnectPacket(RpcPacket):
    pass


class RpcDeclarePacket(RpcPacket):
    """declares receiving queue
    """
    def __init__(self):
        super().__init__()
        self.packet_type = p32(1)


class RpcRetrievePacket(RpcPacket):
    """retrieves a message from receiving queue,
    if message is not ours, ignore, else pop it
    """
    def __init__(self, route_key, corr_id):
        super().__init__()
        self.packet_type = p32(2)
        self.route_key = route_key.encode('UTF-8')
        self.corr_id = corr_id.encode('UTF-8')
        self.length += 8 + len(self.route_key) + len(self.corr_id)

    def into(self):
        return RpcPacket.into(self) + \
            p32(len(self.route_key)) + \
            self.route_key + \
            p32(len(self.corr_id)) + \
            self.corr_id


class RpcCallPacket(RpcPacket):
    """requests for an expression calculation call
    """
    def __init__(self, expr, corr_id, reply_to):
        super().__init__()
        self.packet_type = p32(3)
        self.expr = expr.encode('UTF-8')
        self.reply_to = reply_to.encode('UTF-8')
        self.corr_id = corr_id.encode('UTF-8')
        self.length += 12 + len(self.expr) + len(self.reply_to) + len(self.corr_id)

    def into(self):
        return RpcPacket.into(self) + \
            p32(len(self.reply_to)) + \
            self.reply_to + \
            p32(len(self.corr_id)) + \
            self.corr_id + \
            p32(len(self.expr)) + \
            self.expr


class RpcClosePacket(RpcPacket):
    def __init__(self):
        super().__init__()
        self.packet_type = p32(4)


# Replys
class RpcPacketParseException(Exception):
    pass

class RpcPacketUnavailableException(Exception):
    pass


class RpcReplyPacket(RpcPacket):
    def __init__(self):
        super().__init__()
        self.magic = MAGIC_RECV
        self.packet_type = p32(0xbeef)

    def from_bytes(self, conn):
        reply_bytes = conn.recv(4)
        if not reply_bytes.startswith(MAGIC_RECV):
            raise RpcPacketParseException('invalid reply message header')

        reply_bytes = conn.recv(4)
        length = u32(reply_bytes)

        reply_bytes = conn.recv(length - 8)
        if not reply_bytes.startswith(self.packet_type) and \
                not reply_bytes.startswith(p32(0xbeef + 2)):
            raise RpcPacketParseException('invalid packet type')
        elif reply_bytes.startswith(p32(0xbeef + 2)):
            raise RpcPacketUnavailableException('not ready')

        return reply_bytes[4:]


class RpcReplyDonePacket(RpcReplyPacket):
    pass


class RpcReplyErrorPacket(RpcReplyPacket):
    def __init__(self):
        super().__init__()
        self.packet_type = p32(0xbeef + 1)


class RpcReplyUnavailablePacket(RpcReplyPacket):
    def __init__(self):
        super().__init__()
        self.packet_type = p32(0xbeef + 2)


class RpcReplyResultPacket(RpcReplyPacket):
    def __init__(self):
        super().__init__()
        self.packet_type = p32(0xbeef + 3)
        self.result_bytes = ''

    def from_bytes(self, conn):
        rest = super().from_bytes(conn)
        result_str_len = u32(rest[:4])
        rest = rest[4:]
        if len(rest) != result_str_len:
            raise RpcPacketParseException('invalid result string length')
        self.result_bytes = rest


class RpcConnection(object):
    def __init__(self, host, port):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((host, port))
        self.send_expect(RpcConnectPacket().into(), RpcReplyDonePacket().into())

    def send_expect(self, msg, expecting):
        send_len = self.conn.send(msg)
        if send_len != len(msg):
            raise RpcConnectionException('send message not complete')
        recved = self.conn.recv(len(expecting))
        if recved != expecting:
            raise RpcConnectionException(
                'expecting %s got %s' % (codecs.encode(expecting, 'hex'), codecs.encode(msg, 'hex'))
            )

    def send_with_result(self, msg):
        send_len = self.conn.send(msg)
        if send_len != len(msg):
            raise RpcConnectionException('send message not complete')
        result_packet = RpcReplyResultPacket()
        result_packet.from_bytes(self.conn)
        return result_packet

    def close(self):
        self.conn.send(RpcClosePacket().into())
        self.conn.close()


class RpcClient(object):
    def __init__(self, host, reply_to=None):
        self.conn = RpcConnection(host, SERVICE_PORT)
        if reply_to is None:
            reply_to_queue = self.conn.send_with_result(RpcDeclarePacket().into())
            self.reply_to = reply_to_queue.result_bytes.decode('UTF-8')
        else:
            self.reply_to = reply_to

    def call_request(self, expr):
        corr_id = str(uuid.uuid4())
        self.conn.send_expect(
            RpcCallPacket(expr, corr_id, self.reply_to).into(),
            RpcReplyDonePacket().into()
        )
        return corr_id

    def try_retrieve(self, corr_id):
        return self.conn.send_with_result(RpcRetrievePacket(self.reply_to, corr_id).into())

    def block_wait_result(self, corr_id):
        while True:
            try:
                res = self.try_retrieve(corr_id)
            except RpcPacketUnavailableException:
                continue
            break
        return res


    def call(self, expr):
        corr_id = self.call_request(expr)
        res = self.block_wait_result(corr_id)
        return int(res.result_bytes)

    def close(self):
        self.conn.close()
