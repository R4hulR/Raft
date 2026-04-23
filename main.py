from node import RaftNode
from multiprocessing import Process
from threading import Thread
import time


def run_node(node_id,nei):
    node = RaftNode(node_id,nei)
    Thread(target=node.watchdog,daemon=True).start()
    print("Created watchdog for:",node_id)
    Thread(target=node.server,daemon=True).start()
    print("Created server for:",node_id)
# if __name__ == '__main__':
#     for i in range(5):
#         nei ={1,2,3,4,0} - {i}
#         Process(target=run_node,args=(i,nei), daemon=True).start()
#         print("Created Node:",i)

if __name__ == '__main__':
    import sys
    node_id = int(sys.argv[1])
    nei = {0,1,2,3,4} - {node_id}
    node = RaftNode(node_id, nei)
    Thread(target=node.watchdog).start()
    Thread(target=node.server).start()
