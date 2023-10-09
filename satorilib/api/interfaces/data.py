from abc import ABC, abstractmethod


class FileManager(ABC):
    @abstractmethod
    def read(self, filePath: str):
        pass

    @abstractmethod
    def write(self, filePath: str, data):
        pass

    @abstractmethod
    def append(self, filePath: str, data):
        pass

    @abstractmethod
    def readLine(self, filePath: str, lineNumber: int):
        pass
