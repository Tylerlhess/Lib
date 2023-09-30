'''
this file contains data structures for communication between the server and 
Satroi Neurons
'''


class CheckinDetails:
    ''' 
        {'key': '...',
        'idKey': '...',
        'subscriptionKeys': [],
        'publicationKeys': [],
        'subscriptions': '[]',
        'publications': '[]',
        'pins': '[]'} 
    '''

    def __init__(self, raw: dict):
        self.raw = raw
        self.key: str = raw.get('key')
        self.idKey: str = raw.get('idKey')
        self.subscriptionKeys: list[str] = raw.get('subscriptionKeys')
        self.publicationKeys: list[str] = raw.get('publicationKeys')
        self.subscriptions: str = raw.get('subscriptions')
        self.publications: str = raw.get('publications')
        self.pins: str = raw.get('pins')

    def __str__(self):
        return (
            'CheckinDetails('
            f'\n\tkey: {self.key},'
            f'\n\tidKey: {self.idKey},'
            f'\n\tsubscriptionKeys: {self.subscriptionKeys},'
            f'\n\tpublicationKeys: {self.publicationKeys},'
            f'\n\tsubscriptions: {self.subscriptions},'
            f'\n\tpublications: {self.publications},'
            f'\n\tpins: {self.pins})')
