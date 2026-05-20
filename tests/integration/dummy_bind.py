import socket
import threading
import time
import sys

TCP_PORT = 53
UDP_PORT = 53
HOST = '127.0.0.1'

sockets = []

def bind_tcp():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, TCP_PORT))
    s.listen(1)
    sockets.append(s)
    print(f"[dummy_bind] TCP bound {HOST}:{TCP_PORT}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def bind_udp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, UDP_PORT))
    sockets.append(s)
    print(f"[dummy_bind] UDP bound {HOST}:{UDP_PORT}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    print('[dummy_bind] starting binders (ctrl-c to stop)')
    t1 = threading.Thread(target=bind_tcp, daemon=True)
    t2 = threading.Thread(target=bind_udp, daemon=True)
    t1.start(); t2.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('[dummy_bind] shutting down')
        for s in sockets:
            try:
                s.close()
            except: pass
        sys.exit(0)
