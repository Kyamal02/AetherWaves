import asyncio
import json
import os
import random
import socket
import time

from scapy.all import send
from scapy.layers.inet import IP, UDP

client_id = f"Клиент{random.randint(1000, 9999)}"
# udp_port = random.randint(1024, 65535)
# tcp_port = random.randint(1024, 65535)

server_ip = "213.234.20.2"
server_port = 9999
connection_statuses = {}
registration_confirmed = asyncio.Event()


clients = {}

base_save_path = "/путь/к/каталогу/для/сохранения/"

# Глобальная переменная для хранения экземпляра приложения GUI
app = None

udp_port = None
tcp_port = None



def find_free_port():
    # Создаем сокет
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))  # Привязываем сокет к любому доступному порту на локальной машине
    port = s.getsockname()[1]  # Получаем номер порта, к которому был привязан сокет
    s.close()  # Закрываем сокет
    return port


async def send_udp_packet(dst_ip, dst_port, data):
    """Асинхронная отправка UDP пакета с использованием scapy."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, send_scapy_udp_packet, dst_ip, dst_port, json.dumps(data))


def send_scapy_udp_packet(dst_ip, dst_port, data):
    """Отправляет UDP пакет с использованием scapy."""
    packet = IP(dst=dst_ip) / UDP(sport=udp_port, dport=dst_port) / data
    send(packet)


async def listen_for_incoming_udp_messages(host='0.0.0.0'):
    """Асинхронное прослушивание входящих UDP сообщений."""
    port = find_free_port()
    global udp_port
    udp_port = port
    loop = asyncio.get_running_loop()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((host, port))
        sock.setblocking(False)
        while True:
            data, addr = await loop.sock_recvfrom(sock, 4096)
            message = json.loads(data.decode())
            action = message.get('action')

            # Обработка сообщений
            print(f"Получено от {addr}: {action}")
            if action in ['CLIENTS', 'MESSAGE', 'CONFIRMATION', 'HEARTBEAT', 'ERROR', 'REGISTERED', 'TCP_INFO']:
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



async def send_file(filename, user_id):
    global tcp_connection_confirmed
    ip, port = None
    file_extension = os.path.splitext(filename)[1]  # Получаем расширение файла
    for client in clients:
        if client['client_id'] == user_id:
            ip, port = client['ip'], client['port']
            break


async def get_clients(interval):
    """Периодический запрос списка клиентов."""
    while True:
        data = {"action": "GET", "client_id": client_id, "src_port": udp_port}
        await send_udp_packet(server_ip, server_port, data)
        await asyncio.sleep(interval)


def connection_status(ip, port):
    key = (ip, port)
    return connection_statuses.get(key, {"status": "не найден", "last_active": 0})["status"]


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
        data = {"action": "REGISTER", "client_id": client_id, 'tcp_port': tcp_port}
        await send_udp_packet(server_ip, server_port, data)

        try:
            await asyncio.wait_for(registration_confirmed.wait(), timeout=retry_interval)
            return True
        except asyncio.TimeoutError:
            print(f"Не удалось подключиться к серверу после попытки {attempt + 1}. Повторная попытка...")

    print("Не удалось зарегистрироваться на сервере после нескольких попыток.")
    return False


async def listen_for_incoming_tcp_messages(host = '0.0.0.0'):
    server = await asyncio.start_server(handle_tcp_connection, host, tcp_port)
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    async with server:
        await server.serve_forever()


async def handle_tcp_connection(reader, writer):
    # Читаем данные от клиента
    data = await reader.read(4096)  # Выбираем достаточно большой размер буфера
    message = data.decode()

    # Предполагаем, что сообщение - это JSON
    try:
        message_dict = json.loads(message)
        action = message_dict.get('action')
        print(f"Received action {action} from {writer.get_extra_info('peername')}")

        # Осуществляем различные действия в зависимости от типа запроса
        if action == "some_action":
            # Обработка some_action
            pass

        response = {"status": "success", "message": "Action processed"}
        writer.write(json.dumps(response).encode())
        await writer.drain()

    except json.JSONDecodeError:
        print("Failed to decode message as JSON")

    # Закрываем соединение
    writer.close()




import sys
from PyQt5.QtWidgets import QMessageBox, QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QListWidget, \
    QAction, QMenu, QFileDialog, QListWidgetItem
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
import threading


########################## GUI ############################
class AsyncioGUI(QMainWindow):
    # Определение сигнала для запуска таймера
    start_timer_signal = pyqtSignal(int)

    def __init__(self, loop, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.loop = loop
        self.setWindowTitle("AetherWaves")
        self.setGeometry(100, 100, 400, 400)
        self.connected = False  # Добавляем атрибут для отслеживания состояния подключения

        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)

        self.connect_button = QPushButton("Connect", self)
        self.connect_button.clicked.connect(self.on_connect_or_disconnect)
        self.layout.addWidget(self.connect_button)

        self.clients_listbox = QListWidget(self)
        self.layout.addWidget(self.clients_listbox)

        self.clients_listbox.setContextMenuPolicy(Qt.CustomContextMenu)
        self.clients_listbox.customContextMenuRequested.connect(self.show_context_menu)

        self.setCentralWidget(self.central_widget)

        self.timer = QTimer(self)
        # Подключение сигнала к слоту для установки таймера
        self.start_timer_signal.connect(self.start_timer)

    # Метод для установки таймера
    def start_timer(self, interval):
        self.timer.timeout.connect(self.update_clients_listbox)
        self.timer.start(interval)

    def on_connect_or_disconnect(self):
        if not self.connected:
            asyncio.run_coroutine_threadsafe(self.connect(), self.loop)
        else:
            asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)

    async def connect(self):
        asyncio.run_coroutine_threadsafe(listen_for_incoming_tcp_messages('0.0.0.0'), self.loop)
        asyncio.run_coroutine_threadsafe(listen_for_incoming_udp_messages('0.0.0.0'), self.loop)
        registration_success = await register_with_server()
        if registration_success:
            self.start_timer_signal.emit(1000)
            self.connected = True
            self.connect_button.setStyleSheet("background-color: green;")
            self.connect_button.setText("Disconnect")
            self.show_message("Connected", "Successfully connected to the server!")
            asyncio.run_coroutine_threadsafe(get_clients(10), self.loop)
            asyncio.run_coroutine_threadsafe(check_connections_periodically(10), self.loop)
        else:
            self.show_message("Connection Failed", "Could not connect to the server.")

    async def disconnect(self):
        # Здесь код для отключения от сервера
        self.timer.stop()
        self.clients_listbox.clear()
        self.connected = False
        self.connect_button.setStyleSheet("")
        self.connect_button.setText("Connect")
        self.show_message("Disconnected", "You have been disconnected from the server.")
        # вот тут нужно остановить данные методы
        self.tasks = asyncio.all_tasks(self.loop)

        for task in self.tasks:
            task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Очищаем список задач после отмены
        self.tasks.clear()
        self.timer.stop()

    def update_clients_listbox(self):
        self.clients_listbox.clear()
        for client in clients:  # Предполагается, что 'clients' - это список словарей с данными клиентов
            status = connection_statuses.get((client['ip'], client['port']), {}).get("status")
            item_text = f"{client['client_id']} - {status}"  # Пример формирования текста элемента
            user_id = client['client_id']  # Получаем user_id клиента из данных
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, user_id)
            self.clients_listbox.addItem(item)

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)

    def show_context_menu(self, position):
        # Получаем модельный индекс элемента под курсором мыши
        index = self.clients_listbox.indexAt(position)
        if index.isValid():
            item = self.clients_listbox.item(index.row())
            user_id = item.data(Qt.UserRole)
            context_menu = QMenu(self)
            # Создаем действие "Отправить файл"
            send_file_action = QAction("Отправить файл", self)
            # Используем lambda для передачи user_id в слот
            send_file_action.triggered.connect(lambda: self.on_send_file_triggered(user_id))
            # Добавляем действие в контекстное меню
            context_menu.addAction(send_file_action)
            # Отображаем контекстное меню в текущей позиции курсора
            context_menu.exec_(self.clients_listbox.viewport().mapToGlobal(position))

        # Показываем контекстное меню
        context_menu.exec_(self.clients_listbox.viewport().mapToGlobal(position))
        print(f"Клиент которому пытаюсь отправить файл {user_id}")

    def on_send_file_triggered(self, user_id):
        # Открываем файловый менеджер для выбора файла
        filename, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Все файлы (*)")

        if filename:
            asyncio.run_coroutine_threadsafe(send_file(filename, user_id), self.loop)
            # Здесь код для отправки файла
            print(f"Выбран файл '{filename}' для отправки клиенту '{user_id}'")
            # Вместо print используйте вашу логику для отправки файла


def start_asyncio_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


def main():
    global app
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    asyncio_thread = threading.Thread(target=start_asyncio_loop, args=(loop,), daemon=True)
    asyncio_thread.start()

    app = QApplication(sys.argv)
    gui = AsyncioGUI(loop)

    gui.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
