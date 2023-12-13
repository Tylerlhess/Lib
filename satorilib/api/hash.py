# mainly used for generating unique ids for data and model paths since they must be short

from typing import Union
import base64
import hashlib
import pandas as pd
# from satorilib.concepts import StreamId # recursive import


def generatePathId(path: str = None, streamId: 'StreamId' = None):
    hasher = hashlib.sha1((path or streamId.idString).encode('utf-8'))
    removals = r'\/:*?"<>|=-'
    ret = base64.urlsafe_b64encode(hasher.digest())
    ret = ret.decode("utf-8")
    for char in removals:
        if char in ret:
            ret = ret.replace(char, '-')
    return ret


def historyHashes(df: pd.DataFrame, priorRowHash: str = None) -> pd.DataFrame:
    ''' creates hashes of every row in the dataframe based on prior hash '''
    priorRowHash = priorRowHash or ''
    rowHashes = []
    for index, row in df.iterrows():
        rowStr = priorRowHash + str(index) + str(row['value'])
        # rowHash = hashlib.sha256(rowStr.encode()).hexdigest() # 74mb
        # rowHash = hashlib.md5(rowStr.encode()).hexdigest() # 42mb
        rowHash = hashlib.blake2s(
            rowStr.encode(),
            digest_size=8).hexdigest()  # 27mb / million rows
        rowHashes.append(rowHash)
        priorRowHash = rowHash
    df['hash'] = rowHashes
    return df


def verifyHashes(df: pd.DataFrame, priorRowHash: str = None) -> tuple[bool, Union[pd.DataFrame, None]]:
    '''
    returns success flag and the first row as DataFrame that doesn't pass the 
    hash check or None
    priorRowHash isn't usually passed in because we do the verification on the
    entire dataframe, so by default the first priorRowHash is assumed to be an
    empty string because it's the first peice of data that was recorded. if new
    data was found before it, all the hashes change.
    '''
    priorRowHash = priorRowHash or ''
    for index, row in df.iterrows():
        rowStr = priorRowHash + str(index) + str(row['value'])
        # rowHash = hashlib.sha256(rowStr.encode()).hexdigest() # 74mb
        # rowHash = hashlib.md5(rowStr.encode()).hexdigest() # 42mb
        rowHash = hashlib.blake2s(
            rowStr.encode(),
            digest_size=8).hexdigest()  # 27mb / million rows
        if rowHash != row['hash']:
            print(f'rowHash: {rowHash}')
            return False, row.to_frame().T
        priorRowHash = rowHash
    return True, None
# verifyHashes(df)
# df = pd.DataFrame({'value':[1,2,3,4,5,6], 'hash':['ce8efc6eeb9fc30b','e2cc1a4e70bdba14','42359a663f6c3e30','6278827c73894e0c','c7a6682880ee6f8d','d607268c4f2e75ed']})
