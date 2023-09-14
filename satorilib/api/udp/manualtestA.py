# control + k + shift + s
# cd satorilib/api/udp & python
# client A:
from manager import UDPManager
m = UDPManager(streamIds=None, signature='clientASig', key='clientAKey')

# they should both connect to the rendezvous server
# then they should both connect to each other.
