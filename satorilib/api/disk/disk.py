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
        filename = filename or f'aggregate.{self.ext}'
        return self.safetify(os.path.join(
            (self.loc or Disk.config.dataPath()),
            hash.generatePathId(streamId=self.id),
            filename))

    def exists(self, filename: str = None):
        return os.path.exists(self.path(filename=filename))

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

    def write(self, df: pd.DataFrame = None) -> bool:
        return self.csv.write(
            data=self.memory.flatten(df),
            filePath=self.path())

    def append(self, df: pd.DataFrame = None) -> bool:
        return self.csv.append(
            data=self.memory.flatten(df),
            filePath=self.path())

    def remove(self) -> Union[bool, None]:
        self.csv.remove(filePath=self.path())

    ### read ###

    def read(self) -> Union[pd.DataFrame, None]:
        if not self.exists():
            return None
        return self.csv.read(filePath=self.path())

    def timeExistsInAggregate(self, time: str) -> bool:
        return time in self.read().index

    def getRowCounts(self) -> int:
        ''' returns number of rows in incremental and aggregate tables '''
        try:
            return self.read().shape[0]
        except Exception as _:
            return 0

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
