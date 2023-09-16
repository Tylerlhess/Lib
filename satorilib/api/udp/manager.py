'''
this should probably be moved to the node 
this needs to be re-thought.
listen we have a connection to the Rendezvous server
we also have many streams which represent a topic
we need to make many connections per topic
'''
import json
from time import sleep
from typing import Union
import datetime as dt
from satorilib.api.udp.rendezvous import UDPRendezvousConnection, UDPRendezvousMessage, UDPRendezvousProtocol
from satorilib.api.udp.client import UDPConnection, UDPMessage, UDPProtocol
from satorilib.api.time import datetimeToString, now
from satorilib.concepts import StreamId
from satorilib.api.disk.disk import Disk


class UDPChannel():
    ''' manages a single connection between two nodes over UDP '''

    def __init__(self, streamId: StreamId, ip: str, port: int, localPort: int):
        print(f'UDPChannel 1')
        self.streamId = streamId
        print(f'UDPChannel 2')
        self.disk = Disk(self.streamId)
        print(f'UDPChannel 3')
        self.connection = UDPConnection(
            peerIp=ip,
            peerPort=port,
            port=localPort,
            # todo: messageCallback= function to handle messages
        )
        print(f'UDPChannel 4')
        self.messages: list[UDPMessage] = []
        print(f'UDPChannel 5')
        self.connect()
        print(f'UDPChannel 6')

    def add(self, message: bytes, sent: bool, time: dt.datetime = None):
        self.messages.append(UDPMessage(sent, message, time))
        self.messages = self.orderedMessages()

    def orderedMessages(self):
        ''' returns the messages ordered by UDPMessage.time '''
        return sorted(self.messages, key=lambda msg: msg.time)

    def connect(self):
        self.connection.establish()

    def isReady(self):
        return (
            len([
                msg for msg in self.messages
                if msg.isConfirmedReady() and msg.sent]) > 0 and
            len([
                msg for msg in self.messages
                if msg.isConfirmedReady() and not msg.sent]) > 0)

    def send(self, message: bytes):
        self.connection.send(message)

    def readies(self):
        return [msg for msg in self.messages if msg.isReady()]

    def requests(self):
        return [msg for msg in self.messages if msg.isRequest()]

    def responses(self):
        return [msg for msg in self.messages if msg.isResponse()]

    def myRequests(self):
        return [msg for msg in self.requests() if msg.sent]

    def theirResponses(self):
        return [msg for msg in self.responses() if not msg.sent]

    def mostRecentResponse(self, responses: list[UDPMessage] = None):
        responses = responses or self.theirResponses()
        if len(responses) == 0:
            return None
        return responses[-1]

    def responseAfter(self, time: dt.datetime):
        return [msg for msg in self.theirResponses() if msg.time > time]

    def giveOneObservation(self, time: dt.datetime):
        ''' 
        returns the observation prior to the time of the most recent observation
        '''
        if isinstance(time, dt.datetime):
            time = datetimeToString(time)
        observation = self.disk.lastRowStringBefore(timestap=time)
        if observation is None:
            self.send(UDPProtocol.respondNoObservation())
        else:
            self.send(UDPProtocol.respondObservation(
                time=observation[0],
                data=observation[1]))


class UDPTopic():
    ''' manages all our udp channels for a single topic '''

    def __init__(self, streamId: StreamId):
        self.streamId = streamId
        self.channels: list[UDPChannel] = []

    def readyChannels(self) -> list[UDPChannel]:
        return [channel for channel in self.channels if channel.isReady()]

    def create(self, ip: str, port: int, localPort: int):
        print(f'CREATING: {ip}:{port},{localPort}')
        self.add(UDPChannel(self.streamId, ip, port, localPort))

    def add(self, channel: UDPChannel):
        self.channels.append(channel)

    def broadcast(self, msg: bytes):
        for channel in self.readyChannels():
            channel.send(msg)

    def getOneObservation(self, time: dt.datetime):
        ''' time is of the most recent observation '''
        channels = self.readyChannels()
        msg = UDPProtocol.requestObservationBefore(time)
        sentTime = now()
        for channel in channels:
            channel.send(msg)
        sleep(5)  # wait for responses, natural throttle
        responses: list[Union[UDPMessage, None]] = [
            channel.mostRecentResponse(channel.responseAfter(sentTime))
            for channel in channels]
        responseMessages = [
            response.message for response in responses
            if response is not None]
        mostPopularResponseMessage = max(
            responseMessages,
            key=lambda response: len([
                r for r in responseMessages if r == response]))
        # here we could enforce a threshold, like super majority or something,
        # by saying this message must make up at least 67% of the responses
        # but I don't think it's necessary for now.
        return mostPopularResponseMessage


class UDPManager():
    ''' manages connection to the rendezvous server and all our udp topics '''

    def __init__(self, streamIds: list[StreamId], signature: None, key: None):
        '''
        1. await - set up your connection to the rendezvous server
        2. tell the rendezvous server which streams you want to connect to
        3. for each set up a topic, and all the channels for that topic
        '''
        self.streamIds = self._mapStreamIds(streamIds or [
            StreamId(
                source='s',
                stream='s1',
                author='a',
                target='t',),
            StreamId(
                source='s',
                stream='s2',
                author='a',
                target='t',),
        ])
        self.rendezvous: UDPRendezvousConnection = UDPRendezvousConnection(
            messageCallback=self.handleRendezvousResponse,
            signature=signature,
            key=key,
        )
        # self.topics: dict[str, UDPTopic] = {
        #    topic: UDPTopic(streamId)
        #    for topic, streamId in self.streamIds
        # }
        self.topics: dict[str, UDPTopic] = {}
        self.rendezvous.establish()
        self.sendTopics()
        # for streamId in streamIds:
        # add a new channel - this might be done elsewhere. or in a method.

    def _mapStreamIds(self, streamIds: list[StreamId]):
        return {streamId.topic(): streamId for streamId in streamIds}

    def handleRendezvousResponse(self, data: bytes, address: bytes):
        ''' 
        this is called when we receive a message from the rendezvous server
        '''
        print('received: ', data, address)
        data = data.decode().split('|')
        if data[0] == 'CONNECTION':
            try:
                print('data[1]')
                print(data[1])
                print('self.topics.keys()')
                print(self.topics.keys())
                self.topics.get(data[1]).create(
                    ip=data[2],
                    port=int(data[3]),
                    localPort=int(data[4]))
            except ValueError as e:
                # logging.error('error parsing port', e)
                print(e)

    def sendTopics(self):
        ''' 
        this is called when we want to send our topics to the rendezvous server
        '''
        for topic, streamId in self.streamIds.items():
            if topic not in self.topics:
                self.topics[topic] = UDPTopic(streamId)
                self.rendezvous.send(
                    cmd=UDPRendezvousProtocol.subscribePrefix(),
                    msgs=[
                        "signature doesn't matter during testing",
                        json.dumps({
                            **{'pubkey': 'wallet.pubkey'},
                            # **(
                            #    {
                            #        'publisher': [topic]}
                            # ),
                            **(
                                {
                                    'subscriptions': [topic]
                                }
                            )})])
