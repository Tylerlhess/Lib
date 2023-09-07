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

# punch hole
# equiv: echo 'punch hole' | nc -u -p 20001 x.x.x.x 50002
print('punching hole')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', sport))
sock.sendto(b'0', (ip, dport))

print('ready to exchange messages\n')

# listen for
# equiv: nc -u -l 20001


def listen():
    # Create a file to write the received data.
    with open("received_file.txt", "wb") as f:
        while True:
            # Receive a chunk of data from the client.
            chunk, address = sock.recvfrom(1024)
            if chunk == b"ACK":
                # what? are we sending to someone right now?
            elif chunk == b"FIN":
                #if len(chunk) < 1024:
                break
            else:
                f.write(chunk)
                sock.sendto(b"ACK", address)
    sock.close()

listener = threading.Thread(target=listen, daemon=True)
listener.start()

# send messages
# equiv: echo 'xxx' | nc -u -p 50002 x.x.x.x 20001
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', dport))

while True:
    msg = input('> ')
    sock.sendto(msg.encode(), (ip, sport))
