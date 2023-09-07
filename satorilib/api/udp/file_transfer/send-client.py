# https://udt.sourceforge.io/ UDT
import socket
import sys
import threading

ip = '193.32.127.212'
sport = 50002
dport = 50001

print('\ngot peer')
print('  ip:          {}'.format(ip))
print('  source port: {}'.format(sport))
print('  dest port:   {}\n'.format(dport))

print('punching hole')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', sport))
sock.sendto(b'0', (ip, dport))
print('ready to exchange messages\n')


def listen():
    while True:
        data = sock.recv(1024)
        print('\rpeer: {}\n> '.format(data.decode()), end='')


listener = threading.Thread(target=listen, daemon=True)
listener.start()

# send messages
# equiv: echo 'xxx' | nc -u -p 50002 x.x.x.x 20001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', dport))

# Open the file that you want to transfer.
with open("file.txt", "rb") as f:
    data = f.read()

# Send each chunk to the server.
for chunk in data:
    sock.sendto(chunk, ("127.0.0.1", 5001))

    # Receive an acknowledgement from the server.
    acknowledgement = sock.recv(1024)

    # If the acknowledgement is not received, send the chunk again.
    if not acknowledgement:
        sock.sendto(chunk, ("127.0.0.1", 5001))
