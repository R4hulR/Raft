import time
import random
import threading
import socket
import json


class RaftNode:
    Host = '127.0.0.1'
    PORT = {i:5000+i for i in range(10)}
    def __init__(self, node_id,nei:dict,current_term=0,):
        self.lock = threading.Lock()
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
    
    def send_vote_request(self):
        with self.lock:
            data = {"term":self.current_term,"candidateId":self.node_id,"lastLogIndex":len(self.log)-1, "lastLogTerm":self.log[len(self.log)-1]["term"] if len(self.log) != 0 else 0}
        payload = json.dumps(data).encode("utf-8")
        for ne in self.nei:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock: 
                sock.connect((self.Host,self.PORT[ne]))
                sock.sendall(payload)


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


