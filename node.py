import time
import random
import threading
import socket
import json
import functools
print = functools.partial(print, flush=True)

class RaftNode:
    Host = '127.0.0.1'
    PORT = {i:5000+i for i in range(10)}
    def __init__(self, node_id,nei,current_term=0,):
        self.lock = threading.Lock()
        self.node_id = node_id
        self.current_term = current_term
        self.state = "Follower"
        self.log = []
        self.votedFor = None
        self.commitIndex = 0
        self.lastApplied =0
        self.nei = nei
        self.election_timemout = random.randint(3000,5000)/1000
        self.last_heartbeat = time.time()
        self.N = len(self.nei) + 1
        self.leaderID = None
    
    def send_heartbeat(self):
        try:
            for ne in self.nei:
                with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock: 
                    sock.connect((self.Host,self.PORT[ne]))
                    with self.lock:
                        response = {
                            "type" : "AppendEntries",
                            "term" : self.current_term,
                            "leaderID" : self.node_id,
                            "entries":[]
                        }
                    sock.send(json.dumps(response).encode("utf-8"))
        except Exception as e:
            print("HeartBeat Errror")
    def Leader(self):
        self.nextIndex = {ne: len(self.log) + 1 for ne in self.nei}
        self.matchIndex = {ne: 0 for ne in self.nei}
        while self.state == "Leader":
            self.send_heartbeat()
            time.sleep(50/1000)
    
    def send_vote_request(self):
        print(f"[Node {self.node_id}] send_vote_request called for term {self.current_term}", flush=True)
        with self.lock:
            self.state = "Candidate"
            data = {"type":"vote","term":self.current_term,"candidateId":self.node_id,"lastLogIndex":len(self.log)-1, "lastLogTerm":self.log[len(self.log)-1]["term"] if len(self.log) != 0 else 0}
        payload = json.dumps(data).encode("utf-8")
        totalVote = 1
        
        for ne in self.nei:
            try:
                with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock: 
                    sock.connect((self.Host,self.PORT[ne]))
                    sock.sendall(payload)
                    result = sock.recv(1028).decode('utf-8')
                    voted = json.loads(result)
                    if voted["Voted"]:
                        totalVote+=1
            except Exception as e:
                print(f"[Node {self.node_id}] failed to reach node {ne}: {e}", flush=True)
            
            if totalVote >= self.N//2+1:
                with self.lock:
                    self.state="Leader"
                    print(f"[Node {self.node_id}] I am the LEADER for term {self.current_term}")
                    threading.Thread(target=self.Leader,daemon=True).start()
                break    
    def handle_append_entries(self,conn,payload):
        #Handle request directly from client
        #I Think we need to make Payload["type"] as dictionary , so  payload["type"]["AppendEntries"] == "Leader" if we make "AppendEntries":"Client" or AppendEntries:Server
        if payload["type"]["AppendEntries"] == "Client" and self.state!="Leader":
            #redirect it to Leader
            pass
        #Handle request from Leader
        # Receiver implementation:
        # 1. Reply false if term < currentTerm (§5.1)
        # 2. Reply false if log doesn’t contain an entry at prevLogIndex
        # whose term matches prevLogTerm (§5.3)
        # 3. If an existing entry conflicts with a new one (same index
        # but different terms), delete the existing entry and all that
        # follow it (§5.3)
        # 4. Append any new entries not already in the log
        # 5. If leaderCommit > commitIndex, set commitIndex =
        # min(leaderCommit, index of last new entry)
        else:
            #Hanlde empty entries
            if payload["term"] >= self.current_term:
                with self.lock:
                    if self.state == "Candidate":
                        self.state = "Follower"
                    self.current_term=payload["term"]
                    self.last_heartbeat = time.time()
                    response= {"success":True,"term":self.current_term}
                    print(f"[Node {self.node_id}] Heartbeat from leader {payload['leaderID']}")
                    conn.send(json.dumps(response).encode("utf-8"))
                return True


    def handle_vote_request(self,payload,conn):
        if payload["term"] > self.current_term:
            with self.lock:
                self.current_term = payload["term"]
                self.votedFor = None
                self.state = "Follower"
        elif payload["term"] < self.current_term:
                    response= {"Id":self.node_id,"Voted":False}
                    conn.send(json.dumps(response).encode('utf-8'))
                    conn.close()
                    return
        with self.lock:
            if self.votedFor == None or self.votedFor == payload["candidateId"]:
                if payload["lastLogIndex"]>=len(self.log) and payload["lastLogTerm"]>=self.log[len(self.log)-1]["term"] if len(self.log) != 0 else 0:
                    response = {"Id":self.node_id,"Voted":True}
                    self.votedFor= payload["candidateId"]
                    conn.send(json.dumps(response).encode('utf-8'))
                    print(f"[Node {self.node_id}] Voted for {payload['candidateId']} in term {payload['term']}")
                else:
                    response= {"Id":self.node_id,"Voted":False}
                    conn.send(json.dumps(response).encode('utf-8'))
            else:
                response = {"Id": self.node_id, "Voted": False} 
                conn.send(json.dumps(response).encode('utf-8')) 
                print("sent false")
    def server(self):
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
                sock.bind((self.Host,self.PORT[self.node_id]))
                print(f"[Node {self.node_id}] Server bound to port {self.PORT[self.node_id]}", flush=True)
                sock.listen(128)
                while True:
                    conn,addr = sock.accept()
                    payload = conn.recv(65552).decode('utf-8')
                    payload = json.loads(payload)
                    if payload["type"] == "vote": 
                        self.handle_vote_request(payload,conn)
                    elif payload["type"] == "AppendEntries":
                        self.handle_append_entries(conn,payload)
                    conn.close()
        except Exception as e:
            print(f"Server Error:{e}")
    
        
                
    def watchdog(self):
        time.sleep(5)
        while True:
            try:
                if time.time() - self.last_heartbeat > self.election_timemout:
                    with self.lock:
                        self.current_term+=1
                        self.state = "Candidate"
                        self.votedFor = self.node_id
                        self.election_timemout = random.randint(3000,5000)/1000                        
                        self.last_heartbeat = time.time()
                        threading.Thread(target=self.send_vote_request,daemon=True).start()
                        print(f"[Node {self.node_id}] Election timeout! Starting election for term {self.current_term}")
            except Exception as e:
                print(f"Error at watchdog:{e}")
            time.sleep(50/1000)


