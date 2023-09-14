# control + k + shift + s
# cd satorilib/api/udp & python
# client B:
from manager import UDPManager
m = UDPManager(streamIds=None, signature='clientBSig', key='clientBKey')

# they should both connect to the rendezvous server
# then they should both connect to each other.
