from typing import Union
import os
import pandas as pd
from satorilib.api.interfaces.data import FileManager


class CSVManager(FileManager):
    ''' manages reading and writing to CSV files usind pandas '''

    def _conformBasic(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._conformIndexName(self._conformFlatColumns(df))

    def _conformIndexName(self, df: pd.DataFrame) -> pd.DataFrame:
        df.index.name = None
        return df

    def _conformFlatColumns(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df.columns) == 1:
            df.columns = ['value']
        if len(df.columns) == 2:
            df.columns = ['value', 'hash']
        return df

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._sort(self._dedupe(df))

    def _sort(self, df: pd.DataFrame) -> pd.DataFrame:
        df.sort_index(inplace=True)
        return df

    def _dedupe(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[~df.index.duplicated(keep='last')]

    def _merge(self, dfs: list[pd.DataFrame]) -> pd.DataFrame:
        return self._clean(pd.concat(dfs, axis=0))

    def remove(self, filePath: str) -> Union[bool, None]:
        try:
            os.remove(filePath)
            return True
        except FileNotFoundError as _:
            return None
        except Exception as _:
            return False
        return False

    def read(self, filePath: str) -> pd.DataFrame:
        return self._clean(self._conformBasic(pd.read_csv(filePath, index_col=0)))

    def write(self, filePath: str, data: pd.DataFrame) -> bool:
        try:
            data.to_csv(filePath)
            return True
        except Exception as _:
            return False

    def append(self, filePath: str, data: pd.DataFrame) -> bool:
        try:
            data.to_csv(filePath, mode='a', header=False)
            return True
        except Exception as _:
            return False

    def readLine(self, filePath: str, lineNumber: int) -> Union[pd.DataFrame, None]:
        ''' 0-indexed '''
        try:
            return self._conformBasic(pd.read_table(
                filePath,
                sep=",",
                index_col=0,
                skiprows=lineNumber,
                # skipfooter=lineNumber+1, # slicing is faster; since using c engine
                # engine='python', # required for skipfooter
            ).iloc[[0]])
        except Exception as _:
            return None

