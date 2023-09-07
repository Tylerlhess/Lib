''' this is to test our peristent connection with the rendezvous server. '''
import time
import socket
import threading

rendezvous = ('161.35.238.159', 49152)

# connect to rendezvous
print('connecting to rendezvous server')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 50003))
sock.sendto(b'CHECKIN|0', rendezvous)

receivedBeat: bool = False


def heartbeat():
    global receivedBeat
    beats = 300
    lostBeats = 0
    while True:
        print(f'receivedBeat: {receivedBeat} lostBeats: {lostBeats}')
        if receivedBeat:
            lostBeats = 0
        else:
            lostBeats += 1
        if lostBeats > 5:
            print('lost connection to rendezvous server, should re-establish')
            exit()
        msg = f'BEAT|{beats}'.encode()
        print(f'sending: {msg}')
        sock.sendto(msg, rendezvous)
        beats = int(beats * 1.6182)
        receivedBeat = False
        time.sleep(beats)


listener = threading.Thread(target=heartbeat, daemon=True)
listener.start()

while True:
    data, address = sock.recvfrom(1024)
    print(f'received: {data.decode()}')
    if receivedBeat == True:
        # listener has exited
        exit()
    if data.endswith(b'|beat received'):
        receivedBeat = True
