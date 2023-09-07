import socket
rendezvousServer = ('146.70.134.117', 49152)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 49152))
sock.sendto(b'0', rendezvousServer)
exit()
