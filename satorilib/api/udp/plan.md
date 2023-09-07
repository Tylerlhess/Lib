goal: transfer history direct from node to node.
stretch - this could serve as the pubsub server itself (solution for realtime data too), but that would require some kind of distributed hashgraph to bring it to full fruition, so that's for later.

plan: 
A. establish direct connections
    a. make a meta topic
        1. modify pubsub server so that it creates a companion topic for each stream called meta.
        2. everyone that subscribes to a topic is added to meta, subscribes to it and can broadcast to it.
        3. modify pubsub connection so that we can differentiate between observations on a stream and meta messages
    b. create protocol for meta discussion
        1. this protocol should live in the satorilib/pubsub/meta/protocol.py
        2. it should consist of reqest for history and a response, promise to provide history.
        3. any time a node connects, existing subscribers hear about it in meta and respond 50% of the time with an offer to connect.
        4. if the offer is accepted they use a shared key to connect on the rendevous server. (they can use their pub priv keys, but that's stretch)
    c. create the rendevous server
        1. it should hold connections for 60 seconds
        2. it sould accept a key from each
        3. if any two node match on the key, it provides their ip and ports to each and drops connection.
B. transfer files
    a. establish protocol for file transfer discussion
        1. should consist of history request
        2. history response with a unique number for each packet
        3. completed message with a total of number of packets (on a timed loop in case the other party didn't get it)
        4. request for specific missing packets
        5. repeat 3 and 4 until receiver also responds complete.
    b. save file to disk
        1. safe file to temprorary folder in disk
        2. verify the ipfs hash against the server
        3. if it matches the provider of the stream hash save it to it's proper location, just as we do for ipfs.

that's a lot of moving parts, but if we can get it to work for history, we should be able to get it to work for realtime data too, which would be pretty cool.

alternative to sending the files, we could send the history one item a time... in reverse order, and recreate the file locally... we could ask from everyone... 

B. transfer files
    a. establish a protocol for file history discussion
        1. broadcast, on all our connections a request for the observation just before some UTC time. (now, would be most recent)
        2. everybody responds, take the datetime-value that is agreed upon by the most number of peers. if you have 1 peer, take their word, if you have more, at least 2/3rds must agree.
        3. save to disk (this allows our models to use the data right away and also acts as a cool down so we don't bombard the peers)
        4. repeat with the timestamp of that value
        5. when nobody responds you've reached the beginning of the data.
    b. notice this design requires a node to know about and coordinate communication from multiple nodes
        1. create a management system of a node's connections
        2. including a timeout and an aggregation of responses.

this way is more corruptable. however, we can still check against the history if we make the modification that relayers always aggregate their ipfs. if they do we can compare the singular file to the one we created in theory, making history uncorruptable, however if it doesn't match, we would need the backup solution of requesting the file from the source.
