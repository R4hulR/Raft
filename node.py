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
        self.commitIndex = -1
        self.lastApplied = -1
        self.nei = nei
        self.election_timemout = random.randint(3000,5000)/1000
        self.last_heartbeat = time.time()
        self.N = len(self.nei) + 1
        self.leaderID = None
        self.state_machine = {}
    
    # def send_heartbeat(self):
    #     try:
    #         for ne in self.nei:
    #             with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock: 
    #                 sock.connect((self.Host,self.PORT[ne]))
    #                 with self.lock:
    #                     response = {
    #                         "type" : "AppendEntries",
    #                         "term" : self.current_term,
    #                         "leaderID" : self.node_id,
    #                         "entries":[]
    #                     }
    #                 sock.send(json.dumps(response).encode("utf-8"))
    #     except Exception as e:
    #         print("HeartBeat Errror")
    
    def Leader(self):
        self.nextIndex = {ne: len(self.log) + 1 for ne in self.nei}
        self.matchIndex = {ne: 0 for ne in self.nei}
        
        while self.state == "Leader":
            self.last_heartbeat = time.time()
            self.send_append_entries()
            time.sleep(50/1000)
    
    def send_vote_request(self):
        print(f"[Node {self.node_id}] send_vote_request called for term {self.current_term}", flush=True)
        with self.lock:
            self.state = "Candidate"
            data = {"type":"vote","term":self.current_term,"candidateId":self.node_id,"lastLogIndex": len(self.log) - 1 if len(self.log) != 0 else 0, "lastLogTerm":self.log[len(self.log)-1]["term"] if len(self.log) != 0 else 0}
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
    def apply_entries(self,commitIndex):
        for i in range(self.lastApplied+1, commitIndex+1):
            with self.lock:
                command = self.log[i]["command"]
                parts = command.split()
                if parts[0] == "SET":
                    self.state_machine[parts[1]] = parts[2]
                self.lastApplied = i
            
   
    def handle_append_entries(self,conn,payload):
      
        if payload["term"] >= self.current_term:
            with self.lock:
                if self.state == "Candidate":
                    self.state = "Follower"
                self.current_term=payload["term"]
                self.last_heartbeat = time.time()
                self.leaderID = payload["leaderID"]
            if payload["entries"] :
                prevLogIndex = payload["prevLogIndex"]
                prevLogTerm = payload["prevLogTerm"]
                if prevLogIndex < len(self.log):
                    if self.log[prevLogIndex]["term"]!=prevLogTerm:
                        self.log = self.log[:prevLogIndex]
                        #Term conflict, delete anything after it
                    self.log.extend(payload["entries"])
                elif prevLogIndex == 0:
                    self.log.extend(payload["entries"]) 
                else:
                    conn.send(json.dumps({"success":False,"term":self.current_term}).encode("utf-8"))
                    return
            if payload["leaderCommit"] > self.commitIndex:
                self.commitIndex = min(payload["leaderCommit"], len(self.log) - 1)
                self.apply_entries(self.commitIndex)
            response = {"success":True,"term":self.current_term}
            conn.send(json.dumps(response).encode("utf-8"))
    


    def handle_vote_request(self,payload,conn):
        print(f"[Node {self.node_id}] got vote request from {payload['candidateId']} term {payload['term']} my term {self.current_term}", flush=True)
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
                print(f"lastLogIndex check: {payload['lastLogIndex']} >= {len(self.log)-1}, lastLogTerm check: {payload['lastLogTerm']} >= 0", flush=True)
                myLastTerm = self.log[-1]["term"] if self.log else 0
                if payload["lastLogIndex"] >= len(self.log)-1 and payload["lastLogTerm"] >= myLastTerm:
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
                    elif payload["type"] == "clientRequest":
                        if self.state == "Leader":
                            with self.lock:
                                self.log.append({"term":self.current_term,"command":payload["command"]})
                            prevLogIndex = len(self.log) - 1
                            prevLogTerm = self.log[-1]["term"] if self.log else 0
                            entries = self.log[prevLogIndex:]
                            self.send_append_entries(entries, prevLogIndex, prevLogTerm)
                            conn.send(json.dumps({"success": True}).encode('utf-8'))
                            conn.close()
                        else:
                            conn.send(json.dumps({"redirect":self.leaderID}).encode('utf-8'))
                    elif payload["type"] == "query":
                        conn.send(json.dumps({
                            "log": self.log,
                            "state_machine": self.state_machine,
                            "state": self.state
                        }).encode('utf-8'))
                    conn.close()
        except Exception as e:
            print(f"Server Error:{e}")
    
    
    def send_append_entries(self,entries=[],prevLogIndex=0,prevLogTerm = 0):
        confirmations = 1
        for ne in self.nei:
            try:
                with self.lock:
                    data ={
                        "type": "AppendEntries",
                        "term": self.current_term,
                        "leaderID":self.node_id,
                        "prevLogIndex":prevLogIndex,
                        "prevLogTerm":prevLogTerm,
                        "entries":entries,
                        "leaderCommit": self.commitIndex
                    }
                with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
                    sock.connect((self.Host,self.PORT[ne]))
                    sock.sendall(json.dumps(data).encode("utf-8"))
                    result= sock.recv(1028).decode('utf-8')
                    response = json.loads(result)
                    if response["success"]:
                        confirmations+=1
                if confirmations>=self.N//2+1 and entries:
                    with self.lock:
                        self.commitIndex = len(self.log) -1
                        print(f"[Node {self.node_id}] commitIndex updated to {self.commitIndex}", flush=True)
                    self.apply_entries(self.commitIndex)
                    print(f"[Node {self.node_id}] Committed index {self.commitIndex}")               
            except Exception as e:
                if "10061" not in str(e):
                    print(e)

                
    def watchdog(self):
        time.sleep(10)
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


