# mainly used for generating unique ids for data and model paths since they must be short

import base64
import hashlib
import pandas as pd

# from satorilib.concepts import StreamId # recursive import


def generatePathId(path: str = None, streamId: 'StreamId' = None):
    hasher = hashlib.sha1((path or streamId.idString).encode('utf-8'))
    removals = r'\/:*?"<>|'
    ret = base64.urlsafe_b64encode(hasher.digest())
    ret = ret.decode("utf-8")
    for char in removals:
        if char in ret:
            ret = ret.replace(char, '-')
    return ret


def historyHashes(df: pd.DataFrame, priorRowHash: str = '') -> pd.DataFrame:
    ''' creates hashes of every row in the dataframe using MD5'''
    rowHashes = []
    for index, row in df.iterrows():
        rowStr = priorRowHash + str(index) + str(row)
        rowHash = hashlib.md5(rowStr.encode()).hexdigest()
        rowHashes.append(rowHash)
        priorRowHash = rowHash
    df['hash'] = rowHashes
    return df
