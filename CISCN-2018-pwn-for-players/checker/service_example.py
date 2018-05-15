import struct
import socket
import uuid
import codecs
import threading

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
MAGIC_RECV = b'RPCN'

def construct_result(result):
    print('result %s' % result)
    if type(result) == str:
        result = result.encode('UTF-8')
    print(type(result))
    return MAGIC_RECV + p32(len(result) + 12 + 4) + p32(0xbeef + 3) + p32(len(result)) + \
        result


def handle(client_sock, queue):
    error_packet = MAGIC_RECV + p32(12) + p32(0xbeef + 1)
    retry_packet = MAGIC_RECV + p32(12) + p32(0xbeef + 2)
    done_packet = MAGIC_RECV + p32(12) + p32(0xbeef)

    starting = False

    while True:
        magic = client_sock.recv(4)
        print('magic %s' % magic)
        if magic != MAGIC_SEND:
            client_sock.send(error_packet)
            continue
        length = u32(client_sock.recv(4))
        packet_type = u32(client_sock.recv(4))
        print(packet_type)
        if packet_type == 1:
            # declare
            key = str(uuid.uuid4()).encode('UTF-8')
            print('key %s' % key)
            queue[key] = []
            result = construct_result(key)
            client_sock.send(result)
        elif packet_type == 2:
            # retrieve
            rest = client_sock.recv(length - 12)
            key_len = u32(rest[:4])
            rest = rest[4:]
            key = rest[:key_len]
            rest = rest[key_len:]
            corr_id_len = u32(rest[:4])
            rest = rest[4:]
            corr_id = rest[:corr_id_len]
            print('retrieving key %s' % key)
            try:
                cur_head = queue[key]
                if len(cur_head) == 0:
                    client_sock.send(retry_packet)
                    continue
                if cur_head[0][0] == corr_id:
                    result = construct_result(cur_head[0][1])
                    queue[key] = queue[key][1:]
                    client_sock.send(result)
                else:
                    client_sock.send(retry_packet)
            except KeyError:
                client_sock.send(error_packet)
        elif packet_type == 3:
            # call
            rest = client_sock.recv(length - 12)
            key_len = u32(rest[:4])
            rest = rest[4:]
            key = rest[:key_len]
            rest = rest[key_len:]
            corr_id_len = u32(rest[:4])
            rest = rest[4:]
            corr_id = rest[:corr_id_len]
            rest = rest[corr_id_len:]
            expr_len = u32(rest[:4])
            rest = rest[4:]
            expr = rest[:expr_len]
            print('corr_id %s key %s expr %s' % (corr_id, key, expr))
            expr_res = eval(expr.replace(b'/', b'//'))
            print(queue)
            try:
                queue[key].append((corr_id, str(expr_res)))
                client_sock.send(done_packet)
            except KeyError:
                client_sock.send(error_packet)
        elif packet_type == 0:
            print('connecting')
            if not starting:
                starting = True
                client_sock.send(done_packet)
            else:
                client_sock.send(error_packet)
        elif packet_type == 4:
            break
        else:
            client_sock.send(error_packet)


def service_start():
    queue = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', SERVICE_PORT))
    sock.listen(5)

    while True:
        queue = {}
        (client_sock, addr) = sock.accept()
        print('accpeted')
        threading.Thread(target=handle, args=(client_sock, queue)).start()

    sock.close()

service_start()
