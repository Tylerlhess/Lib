# https://udt.sourceforge.io/ UDT
import time
import socket
import threading

ip = '138.199.6.194'
selfPort = 60002
otherPort = 60001

print('\ngot peer')
print('  ip:          {}'.format(ip))
print('  source port: {}'.format(selfPort))
print('  dest port:   {}\n'.format(otherPort))
print('punching hole')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', selfPort))
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', otherPort))
sock.sendto(b'0', (ip, otherPort))
print('ready to exchange messages\n')


def listen():
    while True:
        data = sock.recv(1024)
        print('\rpeer: {}\n> '.format(data.decode()), end='')


listener = threading.Thread(target=listen, daemon=True)
listener.start()
msg = 0
while True:
    time.sleep(2)
    msg += 2
    print('sending', msg)
    sock.sendto(str(msg).encode(), (ip, selfPort))
