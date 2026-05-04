import socket, json

def send_request(node_id, command):
    PORT = {i: 5000+i for i in range(10)}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(('127.0.0.1', PORT[node_id]))
        request = {"type": "clientRequest", "command": command}
        sock.sendall(json.dumps(request).encode("utf-8"))
        result = json.loads(sock.recv(1028).decode('utf-8'))
        if "redirect" in result:
            print(f"Redirected to node {result['redirect']}")
            return send_request(result['redirect'], command)
        else:
            print(f"Success: {result}")

def get_log(node_id):
    PORT = {i: 5000+i for i in range(10)}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(('127.0.0.1', PORT[node_id]))
        request = {"type": "query", "command": "GET x"}
        sock.sendall(json.dumps(request).encode("utf-8"))
        result = json.loads(sock.recv(1028).decode('utf-8'))
        print(f"Node {node_id}: {result}")



send_request(0, "SET x 5")

for i in range(5):
    get_log(i)