import json
import socket
from scapy.all import send
from scapy.layers.inet import IP, UDP


def udp_server(host='0.0.0.0', port=9999):
    clients = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        print(f"Server listening on UDP port {port}...")
        while True:
            data, addr = s.recvfrom(1024)
            message = json.loads(data.decode())
            ip_src, port_src = addr
            client_id = message.get("client_id")

            if message["action"] == "REGISTER":
                clients[client_id] = {"ip": ip_src, "port": port_src}
                print(f"Registered/Updated client {client_id} from {ip_src}:{port_src}")
                # Отправляем подтверждение регистрации
                send(IP(dst=ip_src)/UDP(sport=port, dport=port_src)/json.dumps({"action": "registered"}))

            elif message["action"] == "GET":
                if client_id in clients:
                    client_list = [{"client_id": cid, "ip": info["ip"], "port": info["port"]} for cid, info in clients.items() if cid != client_id]
                    response_data = json.dumps({"action": "client_list", "clients": client_list})
                    send(IP(dst=ip_src)/UDP(sport=port, dport=port_src)/response_data)
                    print(f"Sent client list to {client_id}")
                else:
                    send(IP(dst=ip_src)/UDP(sport=port, dport=port_src)/json.dumps({"action": "error", "message": "Client not registered"}))

if __name__ == "__main__":
    udp_server()
