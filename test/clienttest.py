import asyncio
import json
import random
import socket
import time

from scapy.all import send
from scapy.layers.inet import IP, UDP

client_id = f"Клиент{random.randint(1000, 9999)}"
src_port = random.randint(1024, 65535)
server_ip = "213.234.20.2"
server_port = 9999
connection_statuses = {}
registration_confirmed = asyncio.Event()
clients = {}
# Глобальная переменная для хранения экземпляра приложения GUI
app = None


async def send_udp_packet(dst_ip, dst_port, data):
    """Асинхронная отправка UDP пакета с использованием scapy."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, send_scapy_packet, dst_ip, dst_port, json.dumps(data))


def send_scapy_packet(dst_ip, dst_port, data):
    """Отправляет UDP пакет с использованием scapy."""
    packet = IP(dst=dst_ip) / UDP(sport=src_port, dport=dst_port) / data
    send(packet)


async def listen_for_incoming_messages(host='0.0.0.0', port=src_port):
    """Асинхронное прослушивание входящих UDP сообщений."""
    loop = asyncio.get_running_loop()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((host, port))
        sock.setblocking(False)
        while True:
            data, addr = await loop.sock_recvfrom(sock, 1024)
            message = json.loads(data.decode())
            action = message.get('action')

            # Обработка сообщений
            print(f"Получено от {addr}: {action}")
            if action in ['CLIENTS', 'MESSAGE', 'CONFIRMATION', 'HEARTBEAT', 'ERROR', 'REGISTERED']:
                await process_incoming_message(action, message, addr)


async def process_incoming_message(action, message, addr):
    """Обработка входящих сообщений от сервера или других клиентов."""
    global clients
    if action == 'CLIENTS':
        print(f"Список клиентов: {message.get('clients', [])}")
        clients = message.get('clients', [])
        for client in clients:
            status = connection_status(client['ip'], client['port'])
            if status != 'confirmed':
                print(f"Попытка подключиться к {client['ip']}:{client['port']} - Статус: {status}")
                await send_udp_packet(client['ip'], client['port'],
                                      {"action": "MESSAGE", "message": f"Привет от {client_id}"})
            else:
                print(f"Уже подключен к {client['ip']}:{client['port']} - Статус: {status}")
    elif action == 'MESSAGE':
        print(f"Сообщение от {addr}: {message.get('message')}")
        await send_udp_packet(addr[0], addr[1],
                              {"action": "CONFIRMATION", "message": f"Сообщение получено от {client_id}"})
    elif action == 'CONFIRMATION':
        await update_connection_status(addr[0], addr[1], 'confirmed')
        print(f"Подтверждение от {addr}: {message.get('message')}")
    elif action == 'HEARTBEAT':
        await update_connection_status(addr[0], addr[1], "confirmed")
    elif action == 'REGISTERED':
        registration_confirmed.set()
        print("Регистрация на сервере выполнена успешно.")
    elif action == 'ERROR':
        print(f"Ошибка с сервера: {message.get('message')}")


async def get_clients(interval):
    """Периодический запрос списка клиентов."""
    while True:
        data = {"action": "GET", "client_id": client_id, "src_port": src_port}
        await send_udp_packet(server_ip, server_port, data)
        await asyncio.sleep(interval)

def connection_status(ip, port):
    key = (ip, port)
    return connection_statuses.get(key, {"status": "не подтвержен", "last_active": 0})["status"]


async def update_connection_status(ip, port, status):
    """Асинхронное обновление статуса соединения."""
    key = (ip, port)
    connection_statuses[key] = {"status": status, "last_active": time.time()}
    print(f"Статус подключения обновлен для {ip}:{port} до {status}")


async def check_connections_periodically(interval):
    """Асинхронная проверка статуса соединений и отправка heartbeat."""
    while True:
        current_time = time.time()
        for key, value in list(connection_statuses.items()):
            ip, port = key
            # Если соединение потеряно, пропускаем
            if value["status"] == "lost":
                continue
            # Если последняя активность была давно, обновляем статус на "lost"
            if value["status"] == "confirmed" and current_time - value["last_active"] > 10:
                print(f"Соединение с {ip}:{port} считается потеряным")
                connection_statuses[key]["status"] = "lost"  # Прямое обновление статуса
            # Отправляем heartbeat всем подтверждённым соединениям
            elif value["status"] == "confirmed":
                await send_udp_packet(ip, port, {"action": "HEARTBEAT", "message": "Heartbeat"})
        await asyncio.sleep(interval)


async def register_with_server(retry_attempts=3, retry_interval=7):
    global registration_confirmed
    for attempt in range(retry_attempts):
        print(f"Попытка {attempt + 1} подключиться к серверу...")
        data = {"action": "REGISTER", "client_id": client_id}
        await send_udp_packet(server_ip, server_port, data)

        try:
            await asyncio.wait_for(registration_confirmed.wait(), timeout=retry_interval)
            return True
        except asyncio.TimeoutError:
            print(f"Не удалось подключиться к серверу после попытки {attempt + 1}. Повторная попытка...")

    print("Не удалось зарегистрироваться на сервере после нескольких попыток.")
    return False


# async def main():
#     # Запускаем прослушивание сообщений
#     asyncio.create_task(listen_for_incoming_messages('0.0.0.0', src_port))
#
#     # Попытка регистрации на сервере
#     registration_success = await register_with_server()
#     if not registration_success:
#         print("Не удалось зарегистрироваться на сервере. Прекращение работы.")
#         return
#
#     # Запуск остальных задач после успешной регистрации
#     tasks = [
#         get_clients(20),
#         check_connections_periodically(10),
#     ]
#     await asyncio.gather(*tasks)
#
#
# if __name__ == "__main__":
#     asyncio.run(main())

########################## GUI ############################
import tkinter as tk
from tkinter import messagebox
import threading


class AsyncioGUI(tk.Tk):
    def __init__(self, loop, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop = loop
        self.title("AetherWaves")
        self.geometry("400x400")

        self.connect_button = tk.Button(self, text="Connect", command=self.on_connect)
        self.connect_button.pack(pady=20)

        self.quit_button = tk.Button(self, text="Quit", command=self.on_quit)
        self.quit_button.pack(pady=20)

        self.clients_listbox = tk.Listbox(self)
        self.clients_listbox.pack(pady=20, fill=tk.BOTH, expand=True)

    def update_clients_listbox(self):
        # Эта функция должна быть вызвана из основного потока
        self.clients_listbox.delete(0, tk.END)
        for client in clients:
            status = connection_statuses.get((client['ip'], client['port']), {}).get("status", "Unknown")
            self.clients_listbox.insert(tk.END, f"{client['client_id']} - {status}")
        # Запланировать следующее обновление
        self.after(5000, self.update_clients_listbox)  # Обновлять каждые 5 секунд

    def on_connect(self):
        asyncio.run_coroutine_threadsafe(self.connect(), self.loop)
        asyncio.run_coroutine_threadsafe(get_clients(10), self.loop)
        asyncio.run_coroutine_threadsafe(check_connections_periodically(10), self.loop)
        self.update_clients_listbox()

    async def connect(self):
        registration_success = await register_with_server()

        if registration_success:
            messagebox.showinfo("Connected", "Successfully connected to the server!")

        else:
            messagebox.showerror("Connection Failed", "Could not connect to the server.")

    def on_quit(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.destroy()


def start_asyncio_loop(loop):
    loop.run_forever()


def main():
    global app
    # Создание нового цикла событий
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Запуск асинхронного цикла в отдельном потоке
    asyncio_thread = threading.Thread(target=start_asyncio_loop, args=(loop,), daemon=True)
    asyncio_thread.start()

    # Создание экземпляра GUI
    app = AsyncioGUI(loop)

    # Запуск прослушивания сообщений как асинхронной задачи
    asyncio.run_coroutine_threadsafe(listen_for_incoming_messages('0.0.0.0', src_port), loop)

    # Запуск GUI
    app.mainloop()

    # Завершение асинхронного цикла после закрытия GUI
    loop.call_soon_threadsafe(loop.stop)
    asyncio_thread.join()
    loop.close()


if __name__ == "__main__":
    main()