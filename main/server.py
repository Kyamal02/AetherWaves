import json
import socket
import threading
import time


def udp_server(host='0.0.0.0', port=9999):
    clients = {}

    def cleanup_clients():
        nonlocal clients
        current_time = time.time()
        timeout = 40  # Тайм-аут в секундах, после которого клиент считается неактивным
        to_delete = [client_id for client_id, client_info in clients.items() if
                     current_time - client_info["last_active"] > timeout]
        for client_id in to_delete:
            del clients[client_id]
            print(f"Клиент {client_id} удален из-за неактивности")

    def periodic_cleanup():
        while True:
            cleanup_clients()
            time.sleep(60)  # Проверка каждую минуту

    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        print(f"Server listening on UDP port {port}...")
        while True:
            data, addr = s.recvfrom(1024)
            message = json.loads(data.decode())
            ip_src, port_src = addr
            client_id = message.get("client_id")

            if message["action"] == "REGISTER":
                clients[client_id] = {"ip": ip_src, "port": port_src, "last_active": time.time()}
                print(f"Зарегистрирован клиент {client_id} из {ip_src}:{port_src}")
                # Отправляем подтверждение регистрации
                s.sendto(json.dumps({"action": "REGISTERED"}).encode(), addr)

            elif message["action"] == "GET":
                if client_id in clients:
                    # Обновляем время последней активности
                    clients[client_id] = {"ip": ip_src, "port": port_src, "last_active": time.time()}
                    client_list = [{"client_id": cid, "ip": info["ip"], "port": info["port"]} for cid, info in
                                   clients.items() if cid != client_id]
                    response_data = json.dumps({"action": "CLIENTS", "clients": client_list})
                    s.sendto(response_data.encode(), addr)
                    print(f"Отправил список клиентов на {client_id}")
                else:
                    s.sendto(json.dumps({"action": "ERROR", "message": "Клиент еще не зарегестрирован на сервере"}).encode(), addr)


if __name__ == "__main__":
    udp_server()
