'''
this is to test our peristent connection with the rendezvous server.
strangely, if the server doesn't respond we don't loose connection.
'''
import time
import socket
import threading

rendezvous = ('161.35.238.159', 49152)

# connect to rendezvous
print('connecting to rendezvous server')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 50003))
sock.sendto(b'CHECKIN|0', rendezvous)


def heartbeat():
    beats = 300
    while True:
        msg = f'BEAT|{beats}'.encode()
        print(f'sending: {msg}')
        sock.sendto(msg, rendezvous)
        beats = beats * 2
        time.sleep(beats)


listener = threading.Thread(target=heartbeat, daemon=True)
listener.start()

while True:
    data, address = sock.recvfrom(1024)
    print(f'received: {data.decode()}')
