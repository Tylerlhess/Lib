import socket
sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 49152))
while True:
    _, address = sock.recvfrom(128)
    print(f'connection from: {address}')
