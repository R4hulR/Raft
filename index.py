import time
import random
import threading
class RaftNode:
    Host = '127.0.0.1'
    PORT = {i:5000+i for i in range(10)}
    def __init__(self, node_id,nei:dict,current_term=0,):
        self.node_id = node_id
        self.current_term = current_term
        self.state = "follower"
        self.log = []
        self.votedFor = None
        self.commitIndex = 0
        self.lastApplied =0
        self.nei = nei
        self.election_timemout = random.randint(150,300)/1000
        self.last_heartbeat = time.time()
    def recieve_AppendEntriesRPC(self, last_heartbeat:time):
        self.last_heartbeat =last_heartbeat


    def watchdog(self):
        while True:
            if time.time() - self.last_heartbeat > self.election_timemout:
               
                self.current_term+=1
                self.state = "candidate"
                self.votedFor = self.node_id
                self.election_timemout = random.randint(150,300)/1000
                self.last_heartbeat = time.time()
                 #send vote rpc request
                pass
            time.sleep(50/1000)


