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

def send_scapy_packet(dst_ip, dst_port, data, retry=3, delay=5):
    packet = IP(dst=dst_ip) / UDP(sport=src_port, dport=dst_port) / json.dumps(data)
    for attempt in range(retry):
        try:
            send(packet)
            break  # Прерываем цикл, если отправка успешна
        except Exception as e:
            print(f"Ошибка отправки: {e}. Попытка {attempt + 1} из {retry}.")
            time.sleep(delay)
            if attempt == retry - 1:  # Последняя попытка
                raise ConnectionError("Не удалось отправить сообщение после нескольких попыток.")

def register_with_server(retry=3, delay=5):
    for attempt in range(retry):
        try:
            send_scapy_packet(server_ip, server_port, {"action": "REGISTER", "client_id": client_id})
            print("Регистрация на сервере успешна.")
            return
        except ConnectionError as e:
            print(f"{e} Попытка переподключения {attempt + 1} из {retry}.")
            time.sleep(delay)
    print("Не удалось зарегистрироваться на сервере после нескольких попыток.")

def periodic_register():
    while True:
        register_with_server()
        time.sleep(60)

def get_clients():
    while True:
        send_scapy_packet(server_ip, server_port, {"action": "GET", "client_id": client_id, "src_port": src_port})
        time.sleep(60)


def connection_status(ip, port):
    key = (ip, port)
    return connection_statuses.get(key, {"status": "not confirmed", "last_active": 0})["status"]

def update_connection_status(ip, port, status):
    key = (ip, port)
    connection_statuses[key] = {"status": status, "last_active": time.time()}
    print(f"Connection status updated for {ip}:{port} to {status}")

def send_message_to_client(ip, port, message):
    send_scapy_packet(ip, port, message)

def listen_for_incoming_messages():
    while True:
        data, addr = client_socket.recvfrom(1024)
        message = json.loads(data.decode())
        action = message.get('action')

        if action == 'client_list':
            for client in message.get('clients', []):
                status = connection_status(client['ip'], client['port'])
                if status != 'confirmed':
                    print(f"Attempting to connect to {client['ip']}:{client['port']} - Status: {status}")
                    send_message_to_client(client['ip'], client['port'], {"action": "message", "message": f"Hello from {client_id}"})
                else:
                    print(f"Already connected to {client['ip']}:{client['port']} - Status: {status}")
        elif action == 'message':
            print(f"Message from {addr}: {message.get('message')}")
            send_message_to_client(addr[0], addr[1], {"action": "confirmation", "message": f"Message received by {client_id}"})
        elif action == 'confirmation':
            update_connection_status(addr[0], addr[1], 'confirmed')
            print(f"Confirmation from {addr}: {message.get('message')}")
        elif action == 'heartbeat':
            update_connection_status(addr[0], addr[1], "confirmed")
        elif action == 'error':
            print(f"Error from server: {message.get('message')}")


def check_connections_periodically():
    while True:
        current_time = time.time()
        for key, value in list(connection_statuses.items()):
            ip, port = key
            # Если соединение потеряно, пропускаем
            if value["status"] == "lost":
                continue
            # Если последняя активность была давно, обновляем статус на "lost"
            if value["status"] == "confirmed" and current_time - value["last_active"] > 10:
                print(f"Connection to {ip}:{port} is considered lost.")
                update_connection_status(ip, port, "lost")
            # Отправляем heartbeat всем подтверждённым соединениям
            elif value["status"] == "confirmed":
                send_message_to_client(ip, port, {"action": "heartbeat", "message": "Heartbeat"})
        time.sleep(10)

def client_main():
    threading.Thread(target=periodic_register, daemon=True).start()
    threading.Thread(target=get_clients, daemon=True).start()
    threading.Thread(target=listen_for_incoming_messages, daemon=True).start()
    threading.Thread(target=check_connections_periodically, daemon=True).start()
    while True:
        time.sleep(10)

if __name__ == "__main__":
    try:
        client_main()
    finally:
        client_socket.close()
