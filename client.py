import json
import random
import socket
import threading
import time

from scapy.all import send
from scapy.layers.inet import IP, UDP

client_id = f"Client{random.randint(1000, 9999)}"
src_port = random.randint(1024, 65535)
server_ip = "213.234.20.2"
server_port = 9999
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.bind(('0.0.0.0', src_port))
connection_statuses = {}

def send_scapy_packet(dst_ip, dst_port, data):
    packet = IP(dst=dst_ip) / UDP(sport=src_port, dport=dst_port) / json.dumps(data)
    send(packet)

def register_with_server():
    send_scapy_packet(server_ip, server_port, {"action": "REGISTER", "client_id": client_id})

def periodic_register():
    while True:
        register_with_server()
        time.sleep(60)

def get_clients():
    while True:
        send_scapy_packet(server_ip, server_port, {"action": "GET", "client_id": client_id, "src_port": src_port})
        time.sleep(60)

# def listen_for_incoming_messages():
#     while True:
#         data, addr = client_socket.recvfrom(1024)
#         message = json.loads(data.decode())
#         action = message.get('action')
#
#         if action == 'client_list':
#             for client in message.get('clients', []):
#                 print(f"send message: {client['ip']}:{client['port']}")
#                 send_message_to_client(client['ip'], client['port'], {"action": "message", "message": f"Hello from {client_id}"})
#         elif action == 'message':
#             print(f"Message from {addr}: {message.get('message')}")
#         elif action == 'error':
#             print(f"Error from server: {message.get('message')}")

def listen_for_incoming_messages():
    while True:
        data, addr = client_socket.recvfrom(1024)
        message = json.loads(data.decode())
        action = message.get('action')

        if action == 'client_list':
            for client in message.get('clients', []):
                if connection_status(client['ip'], client['port']) != 'confirmed':
                    print(f"Sending message to {client['ip']}:{client['port']}")
                    send_message_to_client(client['ip'], client['port'], {"action": "message", "message": f"Hello from {client_id}"})
        elif action == 'message':
            print(f"Message from {addr}: {message.get('message')}")
            send_message_to_client(addr[0], addr[1], {"action": "confirmation", "message": f"Message received by {client_id}"})
        elif action == 'confirmation':
            update_connection_status(addr[0], addr[1], 'confirmed')
            print(f"Confirmation from {addr}: {message.get('message')}")
        elif action == 'error':
            print(f"Error from server: {message.get('message')}")

def connection_status(ip, port):
    key = (ip, port)
    return connection_statuses.get(key, 'not confirmed')

def update_connection_status(ip, port, status):
    key = (ip, port)
    connection_statuses[key] = status

def send_message_to_client(ip, port, message):
    send_scapy_packet(ip, port, message)

def client_main():
    threading.Thread(target=periodic_register, daemon=True).start()
    threading.Thread(target=get_clients, daemon=True).start()
    threading.Thread(target=listen_for_incoming_messages, daemon=True).start()
    while True:
        time.sleep(10)

if __name__ == "__main__":
    try:
        client_main()
    finally:
        client_socket.close()
