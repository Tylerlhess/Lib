''' an api for reading and writing to disk '''

from typing import Union
import os
import pandas as pd
from satorilib.concepts import StreamId
from satorilib.api import memory
from satorilib.api import hash
from satorilib.api.interfaces.model import ModelDataDiskApi
from satorilib.api.disk.utils import safetify, safetifyWithResult
from satorilib.api.disk.model import ModelApi
from satorilib.api.disk.wallet import WalletApi
from satorilib.api.disk.filetypes.csv import CSVManager


class Disk(ModelDataDiskApi):
    ''' single point of contact for interacting with disk '''

    config = None

    @classmethod
    def setConfig(cls, config):
        cls.config = config
        ModelApi.setConfig(config)
        WalletApi.setConfig(config)

    def __init__(
        self,
        df: pd.DataFrame = None,
        id: StreamId = None,
        loc: str = None,
        ext: str = 'parquet',
        **kwargs,
    ):
        self.memory = memory.Memory
        self.csv = CSVManager()
        self.setAttributes(df=df, id=id, loc=loc, ext=ext, **kwargs)
        self.cache: dict[str, int] = {}  # cache of index to row number

    def setAttributes(
        self,
        df: pd.DataFrame = None,
        id: StreamId = None,
        loc: str = None,
        ext: str = 'parquet',
        **kwargs,
    ):
        self.df = df if df is not None else pd.DataFrame()
        self.id = id or StreamId(
            source=kwargs.get('source'),
            author=kwargs.get('author'),
            stream=kwargs.get('stream'),
            target=kwargs.get('target'))
        self.loc = loc
        self.ext = ext
        return self

    def setId(self, id: StreamId = None):
        self.id = id

    ### passthru ###

    @staticmethod
    def defaultModelPath(streamId: StreamId):
        ModelApi.defaultModelPath(streamId)

    @staticmethod
    def saveModel(
        model,
        modelPath: str = None,
        streamId: StreamId = None,
        hyperParameters: list = None,
        chosenFeatures: list = None
    ):
        ModelApi.save(
            model,
            modelPath=modelPath,
            streamId=streamId,
            hyperParameters=hyperParameters,
            chosenFeatures=chosenFeatures)

    @staticmethod
    def loadModel(modelPath: str = None, streamId: StreamId = None):
        return ModelApi.load(modelPath=modelPath, streamId=streamId)

    @staticmethod
    def saveWallet(wallet, walletPath: str = None):
        WalletApi.save(wallet, walletPath=walletPath)

    @staticmethod
    def loadWallet(walletPath: str = None):
        return WalletApi.load(walletPath=walletPath)

    @staticmethod
    def getModelSize(modelPath: str = None):
        return ModelApi.getModelSize(modelPath)

    ### cache ###

    def clearCache(self):
        self.cache = {}

    def updateCacheCount(self, count: int):
        self.cache['count'] = count

    def updateCache(self, df: pd.DataFrame):
        if df is None:
            return
        count = df.shape[0]
        if self.cache.get('count') != count:
            self.clearCache()
            self.updateCacheCount(count)
            if count >= 3:
                self.cache[df.iloc[0]] = df.iloc[[0]].index.values[0]
                self.cache[df.iloc[count-1]
                           ] = df.iloc[[count-1]].index.values[0]
                self.cache[df.iloc[df.iloc[[
                    int(count/2)]]]] = df.iloc[[int(count/2)]].index.values[0]
            i = 4
            while i < int(count/2):
                x = int(count/i)
                self.cache[df.iloc[df.iloc[[x]]]
                           ] = df.iloc[[x]].index.values[0]
                self.cache[df.iloc[df.iloc[[count-x]]]
                           ] = df.iloc[[count-x]].index.values[0]
                i *= 2
        return df

    def searchCache(self, time: str) -> tuple[int, int]:
        before = 0
        after = self.cache['count']*2
        for k, v in self.cache.items():
            if k == time:
                return v, v
            if k < time and v > before:
                before = v
            if k > time and v < after:
                after = v
        return before, after

    ### helpers ###

    def safetify(self, path: str):
        path, created = safetifyWithResult(path)
        if created:
            self.saveName()
        return path

    def path(self, filename: str = None):
        '''
        get the path of a file.
        we generate a hash as the id for the datastream so we can store it in a
        folder and avoid worrying about path length limits. also, we can use the
        entire folder as the ipfs hash for the datastream.
        path lengths should about 170 characters long typically. for examples:
        C:\\Users\\user\\AppData\\Local\\Satori\\models\\qZk-NkcGgWq6PiVxeFDCbJzQ2J0=.joblib
        C:\\Users\\user\\AppData\\Local\\Satori\\data\\qZk-NkcGgWq6PiVxeFDCbJzQ2J0=\\aggregate.parquet
        C:\\Users\\user\\AppData\\Local\\Satori\\data\\qZk-NkcGgWq6PiVxeFDCbJzQ2J0=\\incrementals\\6c0a15fcfa1c4535ab1da046cc1b5dc8.parquet
        '''
        return (
            self.safetify(
                os.path.join(
                    self.loc or Disk.config.dataPath(),
                    hash.generatePathId(streamId=self.id),
                    filename or f'aggregate.{self.ext}')))

    def exists(self, filename: str = None):
        return os.path.exists(self.path(filename=filename))

    def hashDataFrame(self, df: pd.DataFrame = None, priorRowHash: str = '') -> pd.DataFrame:
        ''' first we have to flattent the columns, then rename them '''
        return hash.historyHashes(
            df=self.csv.conformFlatColumns(self.memory.flatten(df)),
            priorRowHash=priorRowHash)

    ### write ###

    def saveHashes(self, df: pd.DataFrame = None) -> bool:
        ''' saves them all to disk '''
        return self.write(hash.historyHashes(df or self.read()))

    def saveName(self) -> bool:
        ''' writes a readme.md file to disk describing dataset '''
        with open(self.path(filename='readme.md'), mode='w+') as f:
            file_data = f.read()
            if not file_data:
                f.write(self.id.topic())
                return True
        return False

    def savePrediction(self, path: str = None, prediction: str = None):
        ''' saves prediction to disk '''
        # todo: we probably should save the predictions to the actual dataset
        #       we can easily parse them out if we use parquet
        #       it's not too much overhead if we use csv
        #       so they should go on the actaul dataset.
        safetify(path)
        with open(path, 'a') as f:
            f.write(prediction)

    def write(self, df: pd.DataFrame) -> bool:
        return self.csv.write(
            filePath=self.path(),
            data=self.updateCache(self.hashDataFrame(df)))

    def append(self, df: pd.DataFrame) -> bool:
        if df.shape[0] == 0:
            return False
        # assumes no duplicates...
        self.updateCacheCount(self.cache['count'] + df.shape[0])
        return self.csv.append(
            filePath=self.path(),
            data=self.hashDataFrame(df, priorRowHash=self.getLastHash()))

    def remove(self) -> Union[bool, None]:
        self.csv.remove(filePath=self.path())

    ### read ###

    def read(self, start: int = None, end: int = None) -> Union[pd.DataFrame, None]:
        if not self.exists():
            return None
        if start == None:
            df = self.csv.read(filePath=self.path())
            self.updateCache(df)
            return df
        return self.csv.readLines(filePath=self.path(), start=start, end=end)

    def timeExistsInAggregate(self, time: str) -> bool:
        return time in self.cache.keys() or time in self.read().index

    def getRowCounts(self) -> int:
        ''' returns number of rows in incremental and aggregate tables '''
        if 'count' in self.cache.keys():
            return self.cache['count']
        try:
            return self.read().shape[0]
        except Exception as _:
            return 0

    def getLastHash(self) -> Union[str, None]:
        ''' gets the hash of the observation at the given time '''
        def getLastHashFromFull():
            df = hash.historyHashes(self.read())
            return df.iloc[df.shape[0]-1].hash

        count = self.cache.get('count')
        if count is None:
            return getLastHashFromFull()
        series = self.read(start=count-1)
        if 'hash' in series:
            return series.hash
        return getLastHashFromFull()

    def getHashOf(self, time: str) -> Union[str, None]:
        ''' gets the hash of the observation at the given time '''
        before, after = self.searchCache(time)
        if before == after:
            series = self.read(start=before).iloc[0]
            if 'hash' in series:
                return series.hash
            return None
        df = self.read(start=before, end=after)
        if df is not None and 'hash' in df and time in df.index:
            return df.loc[time].hash
        return None

    def getHashBefore(self, time: str) -> Union[str, None]:
        ''' gets the hash of the observation just before a given time '''

        def getTheHash(df):

            def getRowBeforeTime(df: pd.DataFrame, target_time: str) -> Union[pd.Series, None]:
                timeBeforeTarget = df[df.index < target_time].index.max()
                if timeBeforeTarget is not pd.NaT:
                    return df.loc[timeBeforeTarget]
                return None

            if 'hash' not in df:
                row = getRowBeforeTime(df, time)
                if row is not None:
                    return row.hash
            return None

        before, after = self.searchCache(time)
        if before == after:
            series = self.read(start=before-1).iloc[0]
            if 'hash' in series:
                return series.hash
        else:
            theHash = getTheHash(self.read(start=before, end=after))
            if theHash is not None:
                return theHash
        return getTheHash(self.read())

    def getObservationBefore(self, time: str) -> Union[pd.DataFrame, None]:
        ''' gets the observation just before a given time '''

        def getTheRow(df):

            def getRowBeforeTime(df: pd.DataFrame, target_time: str) -> Union[pd.Series, None]:
                timeBeforeTarget = df[df.index < target_time].index.max()
                if timeBeforeTarget is not pd.NaT:
                    return df.loc[[timeBeforeTarget]]
                return None

            row = getRowBeforeTime(df, time)
            if row is not None:
                return row.hash
            return None

        before, after = self.searchCache(time)
        if before == after:
            df = self.read(start=before-1)
            if df is not None and time in df.index:
                return df
        else:
            theRow = getTheRow(self.read(start=before, end=after))
            if theRow is not None:
                return theRow
        return getTheRow(self.read())

    def gather(
        self,
        targetColumn: 'str|tuple[str]',
        streamIds: list[StreamId] = None,
    ) -> pd.DataFrame:
        ''' retrieves the targets and merges them '''
        if streamIds is None:
            source = self.id.source or self.df.columns.levels[0]
            author = self.id.author or self.df.columns.levels[1]
            stream = self.id.stream or self.df.columns.levels[2]
            try:
                target = self.id.target or self.df.columns.levels[3]
            except AttributeError:
                target = None
            streamId = StreamId(
                source=source,
                author=author,
                stream=stream,
                target=target)
            df = self.read()
            if df is None:
                return None
            return self.memory.expand(df=df, streamId=streamId)
        dfs = []
        for streamId in streamIds:
            df = Disk(id=streamId).read()
            if df is None:
                continue
            dfs.append(self.memory.expand(df=df, streamId=streamId))
        return self.memory.merge(dfs=dfs, targetColumn=targetColumn)
