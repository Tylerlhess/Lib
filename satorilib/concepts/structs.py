from typing import Union
import json
import pandas as pd
import datetime as dt
from functools import partial
# from satorilib.api.hash import generatePathId


class StreamId:
    ''' unique identifier for a stream '''

    def __init__(
        self,
        source: str,
        author: str,
        stream: str,
        target: str = '',
    ):
        self.__source = source
        self.__author = author
        self.__stream = stream
        self.__target = target
        # disallowing target to be None (for hashability) means an empty string
        # is not a valid target, which it might be in the real world. so we
        # allow target to be None, indicating that a stream observation is a
        # value in and of itself, rather than structure of values (such as a
        # dictionary or a json object in which case the target would be a string
        # corresponding to the key, or list in which case target might be the
        # index).

    @property
    def source(self):
        return self.__source

    @property
    def author(self):
        return self.__author

    @property
    def stream(self):
        return self.__stream

    @property
    def target(self):
        return self.__target

    @staticmethod
    def itemNames():
        return ['source', 'author', 'stream', 'target']

    def topic(self, asJson: bool = True, authorAsPubkey=False) -> Union[str, dict[str, str]]:
        '''
        the topic (id) for this stream.
        this is how the pubsub system identifies the stream.
        '''
        if asJson:
            return self.topicJson(authorAsPubkey=authorAsPubkey)
        return {
            'source': self.__source,
            'pubkey' if authorAsPubkey else 'author': self.__author,
            'stream': self.__stream,
            'target': self.__target}

    def topicJson(self, authorAsPubkey=False) -> str:
        '''
        the topic (id) for this stream.
        this is how the pubsub system identifies the stream.
        '''
        return json.dumps(self.topic(asJson=False, authorAsPubkey=authorAsPubkey))

    @property
    def id(self):
        return (self.__source, self.__author, self.__stream, self.__target)

    @property
    def idString(self):  # todo: make this .id and the .key a tuple
        return (
            (self.__source or '') +
            (self.__author or '') +
            (self.__stream or '') +
            (self.__target or ''))

    def __repr__(self):
        return str({
            'source': self.__source,
            'author': self.__author,
            'stream': self.__stream,
            'target': self.__target})

    def __str__(self):
        return str(self.__repr__())

    def __eq__(self, other):
        if isinstance(other, StreamId):
            return (
                self.source == other.source and
                self.author == other.author and
                self.stream == other.stream and
                self.target == other.target)
        return False

    def __hash__(self):
        '''
        note: target can be None meaning, the stream is not a dictionary of
        values. yet we still have to hash the object, thus the use of np.inf
        which only has the side effect of barring np.inf as a valid target when
        a stream by the same id and no target also exists. (essentially safe).
        this is a better choice than 0 or -1 since a stream observation could be
        a list of values and the target an index for that list.

        note 0: the above note is helpful, but np.inf cannot be concatenated
        with strings so it would be preferable to use a random string here, 
        rather than an empty string becuase it would be less likely to clash.
        we'll use the Mersenne Twister algorithm with seed 'dR3jS9lMqXcTfYvA':
        q7jDmL8kV4HvCnX

        note 1: that's a great idea, but here's the situation: the server has
        this same problem and solves it with an empty string. So since this 
        problem manifest at the domain level, not merely in this equality check,
        we'll use that solution for now.

        note 2: alright, so that doesn't work in this endpoint: 
        /remove_stream/<source>/<stream>/<target> because target is an empty
        string. so. target always has to be a non-null non-empty string. I think
        the default should be a - then. To be honest... the best solution is to
        get rid of target altogether. the domain seems broken here because why
        have hierarchy at all if it's limited to just 3 levels. You have to deal
        with all that complexity, but you don't get the versatility of a real
        hierarchy. so we can either fix the domain to remove target altogether,
        or we can use a '-' as the default. 3 levels would be fine if it was EAV
        but it's not. the better domain design would be unique streamid (a hash)
        with a lookup table to what that stream corresponds to, and allow that
        to be an unlimited hierarchy requiring at least source. for now we'll
        use the '-' solution which requires a server change anyway.

        note 3: instead of that I decided to change the endpoint to 
        /remove_stream/<topic> and parse out the topic instead. it's just less
        work for the same quality work around.
        '''
        return hash(
            self.__source +
            self.__author +
            self.__stream +
            (self.__target or ''))

    # @property
    # def generateHash(self) -> str:
    #    return generatePathId(streamId=self)

    @property
    def key(self):
        return self.id

    def new(
        self,
        source: str = None,
        author: str = None,
        stream: str = None,
        target: str = None,
    ):
        return StreamId(
            source=source or self.source,
            author=author or self.author,
            stream=stream or self.stream,
            target=target or self.target)

    @staticmethod
    def fromMap(map: dict = None):
        return StreamId(
            source=(map or {}).get('source'),
            author=(map or {}).get('author', (map or {}).get('pubkey')),
            stream=(map or {}).get('stream', (map or {}).get('name')),
            target=(map or {}).get('target'))

    @staticmethod
    def fromTopic(topic: str = None):
        return StreamId.fromMap(json.loads(topic or '{}'))


# now that we've made the StreamId hashable this is basically unnecessary.
class StreamIdMap():
    def __init__(self, streamId: StreamId = None, value=None):
        if streamId is None:
            self.d = dict()
        else:
            self.d = {streamId: value}

    def __repr__(self):
        return str(self.d)

    def __str__(self):
        return str(self.__repr__())

    def add(self, streamId: StreamId, value=None):
        self.d[streamId] = value

    def addAll(self, streamIds: list[StreamId], values: list[StreamId]):
        for streamId, value in zip(streamIds, values):
            self.add(streamId, value)

    def keys(self):
        return self.d.keys()

    def streams(self):
        return {k.new(clearTarget=True) for k in self.keys()}

    @staticmethod
    def _condition(key: StreamId, streamId: StreamId, default: bool = True):
        return all([
            x == k or (x is None and default)
            for x, k in zip(
                [streamId.source, streamId.author,
                    streamId.stream, streamId.target],
                [key.source, key.author, key.stream, key.target])])

    def remove(self, streamId: StreamId, greedy: bool = True):
        condition = partial(
            StreamIdMap._condition,
            streamId=streamId, default=greedy)
        removed = []
        for k in self.d.keys():
            if condition(k):
                removed.append(k)
        for k in removed:
            del self.d[k]
        return removed

    def get(self, streamId: StreamId = None, default=None, greedy: bool = False):
        if streamId is None:
            return self.d
        condition = partial(
            StreamIdMap._condition,
            streamId=streamId, default=greedy)
        matches = [
            self.d.get(k) for k in self.d.keys() if condition(k)]
        return matches[0] if len(matches) > 0 else default

    def getAll(self, streamId: StreamId = None, greedy: bool = True):
        if streamId is None:
            return self.d
        condition = partial(
            StreamIdMap._condition,
            streamId=streamId, default=greedy)
        return {k: v for k, v in self.d.items() if condition(k)}

    def isFilled(self, streamId: StreamId, greedy: bool = True):
        condition = partial(
            StreamIdMap._condition,
            streamId=streamId, default=greedy)
        matches = [
            self.d.get(k) is not None for k in self.d.keys() if condition(k)]
        return len(matches) > 0 and all(matches)

    def getAllAsList(self, streamId: StreamId = None, greedy: bool = True):
        matches = self.getAll(streamId, greedy=greedy)
        return [(k, v) for k, v in matches.items()]


class Stream:
    def __init__(
        self,
        streamId: StreamId,
        cadence: int = None,
        offset: int = None,  # unused... for now
        datatype: str = None,  # unused... for now
        description: str = None,  # unused... for now
        tags: str = None,  # unused... for now
        url: str = None,  # unused... for now
        uri: str = None,
        headers: str = None,
        payload: str = None,
        hook: str = None,
        history: str = None,
        ts: str = None,
        predicting: StreamId = None,
        reason: StreamId = None,
        reason_is_primary: bool = None,
        **kwargs
    ):
        self.streamId = streamId
        self.cadence = cadence
        self.offset = offset
        self.datatype = datatype
        self.description = description
        self.tags = tags
        self.url = url
        self.uri = uri
        self.headers = headers
        self.payload = payload
        self.hook = hook
        self.history = history
        self.ts = ts
        self.predicting = predicting
        self.reason = reason
        self.reason_is_primary = reason_is_primary
        self.kwargs = kwargs

    def __str__(self):
        return str(vars(self))

    def __repr__(self):
        return self.__str__()

    @property
    def id(self):
        return self.streamId

    @staticmethod
    def fromMap(rep: dict = None):
        def extractKnownKwarg(key: str, rep: dict = None):
            rep = rep or {}
            kwargs = rep.get('kwargs', {})
            if key in kwargs.keys() and key not in rep.keys():
                rep[key] = kwargs.get(key)
                rep['kwargs'] = {k: v for k, v in kwargs.items() if k != key}
            return rep

        def extractPredicting(key: str, rep: dict = None):
            predictionKeys = [
                f'{key}_source',
                f'{key}_author',
                f'{key}_stream',
                f'{key}_target',]
            rep = rep or {}
            if all([x in rep.keys() for x in predictionKeys]):
                rep[key] = StreamId.fromMap({
                    k.replace(f'{key}_', ''): v
                    for k, v in rep.items()
                    if k in predictionKeys})
                rep = {
                    k: v for k, v in rep.items() if k not in predictionKeys}
            return rep

        rep = extractKnownKwarg('ts', rep)
        rep = extractKnownKwarg('reason_is_primary', rep)
        rep = extractPredicting('predicting', rep)  # publish prediction of x
        rep = extractPredicting('reason', rep)  # subscribing to predict x
        return Stream(
            streamId=StreamId.fromMap(rep),
            **{k: rep[k] for k in rep.keys() if k not in StreamId.itemNames()})

    def asMap(self, noneToBlank=False, includeTopic=True):
        return {
            **({
                k: v if v is not None else ''
                for k, v in vars(self).items()} if noneToBlank else vars(self)),
            **({'topic': self.streamId.topic()} if includeTopic else {})}


class StreamsOverview():

    def __init__(self, engine):
        self.engine = engine
        # self.demo = [{'source': 'Streamr', 'stream': 'DATAUSD/binance/ticker', 'target': 'Close', 'subscribers': '99', 'accuracy': [.5, .7, .8, .85, .87, .9, .91, .92, .93],
        #              'prediction': 15.25, 'value': 15, 'values': [12, 13, 12.5, 13.25, 14, 13.5, 13.4, 13.7, 14.2, 13.5, 14.5, 14.75, 14.6, 15.1], 'predictions': [3, 2, 1]}]
        self.overview = [{'source': '-', 'stream': '-', 'target': '-', 'subscribers': '-',
                          'accuracy': '-', 'prediction': '-', 'value': '-', 'values': [3, 2, 1], 'predictions': [3, 2, 1]}]
        self.viewed = False
        self.setIt()

    def setIt(self):
        self.overview = [model.overview() for model in self.engine.models]
        self.viewed = False

    def setViewed(self):
        self.viewed = True


class Observation:

    def __init__(self, raw, **kwargs):
        self.raw = raw
        self.value: Union[str, None] = None
        self.data: Union[dict, None] = None
        self.hash: Union[dict, None] = None
        self.time: Union[str, None] = None
        self.streamId: Union[StreamId, None] = None
        self.observationHash: Union[int, None] = None
        self.df: pd.Union[DataFrame, None] = None
        self.observationTime: Union[str, None] = None
        self.target: Union[str, None] = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    @staticmethod
    def parse(raw):
        if (isinstance(raw, dict) and
            'topic' in raw.keys() and
            'data' in raw.keys()
            # 'hash' in raw.keys() and 'time' in row.keys() # should be required
            ) or (
            isinstance(raw, str) and
            '"topic":' in raw and
            '"data":' in raw
            # '"hash":' in raw and '"time":' in row # should be required

        ):
            return Observation.fromTopic(raw)
        return Observation.fromGuess(raw)

    @staticmethod
    def fromTopic(raw):
        '''
        this is the structur that hte Satori PubSub delivers data in: {
            'topic': '{"source": "satori", "author": "02a85fb71485c6d7c62a3784c5549bd3849d0afa3ee44ce3f9ea5541e4c56402d8", "stream": "WeatherBerlin", "target": "temperature"}',
            'data': 4.2,
            'hash': 'abc'}
        '''
        if isinstance(raw, str):
            j = json.loads(raw)
        elif isinstance(raw, dict):
            j = raw
        topic = j.get('topic', None)
        streamId = StreamId.fromTopic(topic)
        observedTime = j.get('time', str(dt.datetime.utcnow()))
        observationHash = j.get('observationHash', None)
        value = j.get('data', None)
        target = None
        df = pd.DataFrame(
            {
                (
                    streamId.source,
                    streamId.author,
                    streamId.stream,
                    streamId.target):
                [value] + (
                    [('StreamObservationId', observationHash)]
                    if observationHash is not None else [])},
            index=[observedTime])
        # I don't understand whey we still have a StreamObservationId
        # or the multicolumn identifier... maybe it's for the engine?
        # I think we should just save it to disk like this:
        # observationHash = j.get('hash', None)
        # df = pd.DataFrame(
        #    {'value': [value],  'hash': [observationHash]},
        #    index=[observedTime])
        return Observation(
            raw=raw,
            topic=topic,
            streamId=streamId,
            observedTime=observedTime,
            observationHash=observationHash,
            value=value,
            target=target,
            df=df)

    @staticmethod
    def fromGuess(raw):
        ''' {
                'source:"streamrSpoof",'
                'author:"pubkey",'
                'stream:"simpleEURCleaned",'
                'observation': 3675,
                'time': "2022-02-16 02:52:45.794120",
                'content': {
                    'High': 0.81856,
                    'Low': 0.81337,
                    'Close': 0.81512}}
            note: if observed-time is missing, define it here.
        '''
        if isinstance(raw, str):
            j = json.loads(raw)
        elif isinstance(raw, dict):
            j = raw
        elif isinstance(raw, tuple):
            j = {}
            for k, v in raw:
                j[k] = v
        else:
            j = raw
        observedTime = j.get('time', str(dt.datetime.utcnow()))
        observationHash = j.get('observationHash', None)
        content = j.get('content', {})
        streamId = StreamId(
            source=j.get('source', None),
            author=j.get('author', None),
            stream=j.get('stream', None),
            target=j.get('target', None))
        value = None
        if isinstance(content, dict):
            if len(content.keys()) == 1:
                streamId.new(target=content.keys()[0])
                value = content.get(streamId.target)
            df = pd.DataFrame(
                {
                    (
                        streamId.source,
                        streamId.author,
                        streamId.stream,
                        target): values
                    for target, values in list(
                        content.items()) + (
                            [('StreamObservationId', observationHash)]
                            if observationHash is not None else [])},
                index=[observedTime])
        # todo: handle list
            # elif isinstance(content, list): ...
        else:
            value = content
            df = pd.DataFrame(
                {(
                    streamId.source,
                    streamId.author,
                    streamId.stream,
                    None): [
                    content] + (
                        [('StreamObservationId', observationHash)]
                        if observationHash is not None else [])},
                index=[observedTime])
        return Observation(
            raw=raw,
            content=content,
            observedTime=observedTime,
            observationHash=observationHash,
            streamId=streamId,
            value=value,
            df=df)

    @property
    def key(self):
        return self.streamId
