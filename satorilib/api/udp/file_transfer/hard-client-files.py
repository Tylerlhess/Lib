'''
this script includes the basic protocol for sending files over udp
it's basically working, but doesn't have all the features yet (mostly commented
out code) of managing the file tranfer perfectly (ording and handling missing
packets).

decided that we might not need to transfer files over udp, and instead tranfer
observations one at a time. so stopped development on this half way through.

you can seed the desgin from the code below: sender numbers each packet (chunk)
and says "COMPLETE total_chunks" when done. the complete message should be in a
loop incase the receiver doesn't get it the first time. the reciever sends 
"REQUEST:missing" if it's missing any packets. the sender sends the missing
packets and this process repeats until all packets are received, at that point
the receiver says "COMPLETED" and no more communication is required. then the
receiver can write all the chunks to a file in their proper order.
'''

# https://udt.sourceforge.io/ UDT
import os
import time
import socket
import threading

ip = '138.199.6.194'
selfPort = 50002
otherPort = 50001
sender = False
filePath = __file__  # send this file as example

print('peer ip:    {}'.format(ip))
print('self port:  {}'.format(selfPort))
print('other port: {}\n'.format(otherPort))
print('punching hole')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', selfPort))
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', otherPort))
sock.sendto(b'0', (ip, otherPort))  # not necessary
print('ready to exchange messages\n')


def listen(
    #    exitEvent
):
    # chunks = {}
    # Wait for the initial message from the receiver to initiate the file transfer
    print('waiting...')
    initial_message, addr = sock.recvfrom(1024)
    print('Received initial message:', initial_message.decode(), 'from', addr)
    # now we listen for file...
    # assumes initial_message is INITIATE_TRANSFER
    while True:
        # if exitEvent.is_set():
        #    exit(0)
        data, addr = sock.recvfrom(1024)
        print('received', data)
    #    if data.startswith(b'COMPLETE'):
    #        total_chunks = data.split(b':', 1)[1]
    #        missing_chunks = []
    #        for chunk_num in range(total_chunks):
    #            if str(chunk_num) not in received_chunks:
    #                missing_chunks.append(chunk_num)
    #        if missing_chunks:
    #            # Request missing chunks from the sender
    #            request = f'REQUEST:{",".join(str(chunk) for chunk in missing_chunks)}'.encode(
    #            )
    #            sock.sendto(request, addr)
    #        else:
    #            # All chunks received, exit the loop
    #            break
    #    else:
    #        # verify it's part of the file somehow first ...
    #        num, partialData = data.split(b':', 1)
    #        chunks[num] = partialData
    #        print('num:', num)
    #        # Send acknowledgment back to the sender ( not on every chunk...)
    #         ack = f'ACK:{chunk_num}'.encode()
    #         sock.sendto(ack, addr)
    # # Send completion acknowledgment back to the sender
    # completion_ack = b'COMPLETED'
    # sock.sendto(completion_ack, addr)
    # # Write the received chunks to the file
    # with open('received_file.txt', 'ab') as file:
    #     for chunk_num in range(total_chunks):
    #         file.write(received_chunks[str(chunk_num)])


if not sender:
    # exitEvent = threading.Event()
    listener = threading.Thread(
        target=listen,
        # args=(exitEvent,),
        daemon=True)
    listener.start()
# example of sending string messages
# msg = 0
# while True:
#   time.sleep(2)
#   msg += 2
#   print('sending', msg)
#   sock.sendto(str(msg).encode(), (ip, selfPort))


def send():
    # Send the initial message to initiate the file transfer
    initial_message = b'INITIATE_TRANSFER'
    sock.sendto(initial_message, (ip, selfPort))
    # Open the file in binary mode for reading
    chunk_size = 512
    # unused variable
    # total_chunks = os.path.getsize(filePath) // chunk_size + 1
    with open(filePath, 'rb') as file:
        chunk_num = 0
        while True:
            # Read a chunk of data from the file
            chunk_data = file.read(chunk_size)
            # Check if there's no more data to send
            if not chunk_data:
                break
            # Construct the message with chunk number and data
            message = f'{chunk_num}:{chunk_data.decode()}'.encode()
            # Send the chunk to the receiver
            sock.sendto(message, (ip, selfPort))
            chunk_num += 1

    # Send the completion message
    completion_message = b'COMPLETE'
    sock.sendto(completion_message, (ip, otherPort))

    # Wait for the completion acknowledgment from the receiver
    completion_ack, addr = sock.recvfrom(1024)
    if completion_ack == b'COMPLETED':
        print('File transfer completed successfully.')

    # Close the socket
    # sock.close()
if sender:
    # comment this out on reciever side
    send()

time.sleep(10)
# exitEvent.set()
