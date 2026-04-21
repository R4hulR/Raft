from node import RaftNode
from multiprocessing import Process
from threading import Thread
import time


def run_node(node_id,nei):
    node = RaftNode(node_id,nei)
    Thread(target=node.watchdog,daemon=True).start()
    Thread(target=node.server,daemon=True).start()
if __name__ == '__main__':
    for i in range(5):
        nei ={1,2,3,4,0} - {i}
        Process(target=run_node,args=(i,nei), daemon=True).start()
    while True:    
        time.sleep(12345555)
