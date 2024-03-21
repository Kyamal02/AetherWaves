# import asyncio
# import json
# import os
# import random
# import socket
# import time
# import uuid
#
# from scapy.all import send
# from scapy.layers.inet import IP, UDP
#
# client_id = f"Клиент{random.randint(1000, 9999)}"
# src_port = random.randint(1024, 65535)
# server_ip = "213.234.20.2"
# server_port = 9999
# connection_statuses = {}
# registration_confirmed = asyncio.Event()
#
# clients = {}
#
# file_parts_storage = {}
# base_save_path = "/путь/к/каталогу/для/сохранения/"
#
# # Глобальная переменная для хранения экземпляра приложения GUI
# app = None
#
#
#
# async def send_udp_packet(dst_ip, dst_port, data):
#     """Асинхронная отправка UDP пакета с использованием scapy."""
#     loop = asyncio.get_running_loop()
#     await loop.run_in_executor(None, send_scapy_packet, dst_ip, dst_port, json.dumps(data))
#
#
# def send_scapy_packet(dst_ip, dst_port, data):
#     """Отправляет UDP пакет с использованием scapy."""
#     packet = IP(dst=dst_ip) / UDP(sport=src_port, dport=dst_port) / data
#     send(packet)
#
#
# async def listen_for_incoming_messages(host='0.0.0.0', port=src_port):
#     """Асинхронное прослушивание входящих UDP сообщений."""
#     loop = asyncio.get_running_loop()
#     with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
#         sock.bind((host, port))
#         sock.setblocking(False)
#         while True:
#             data, addr = await loop.sock_recvfrom(sock, 4096)
#             message = json.loads(data.decode())
#             action = message.get('action')
#
#             # Обработка сообщений
#             print(f"Получено от {addr}: {action}")
#             if action in ['CLIENTS', 'MESSAGE', 'CONFIRMATION', 'HEARTBEAT', 'ERROR', 'REGISTERED', 'FILE']:
#                 await process_incoming_message(action, message, addr)
#
#
# async def process_incoming_message(action, message, addr):
#     """Обработка входящих сообщений от сервера или других клиентов."""
#     global clients
#     if action == 'CLIENTS':
#         print(f"Список клиентов: {message.get('clients', [])}")
#         clients = message.get('clients', [])
#         for client in clients:
#             status = connection_status(client['ip'], client['port'])
#             if status != 'confirmed':
#                 print(f"Попытка подключиться к {client['ip']}:{client['port']} - Статус: {status}")
#                 await send_udp_packet(client['ip'], client['port'],
#                                       {"action": "MESSAGE", "message": f"Привет от {client_id}"})
#             else:
#                 print(f"Уже подключен к {client['ip']}:{client['port']} - Статус: {status}")
#     elif action == 'MESSAGE':
#         print(f"Сообщение от {addr}: {message.get('message')}")
#         await send_udp_packet(addr[0], addr[1],
#                               {"action": "CONFIRMATION", "message": f"Сообщение получено от {client_id}"})
#     elif action == 'CONFIRMATION':
#         await update_connection_status(addr[0], addr[1], 'confirmed')
#         print(f"Подтверждение от {addr}: {message.get('message')}")
#     elif action == 'HEARTBEAT':
#         await update_connection_status(addr[0], addr[1], "confirmed")
#     elif action == 'REGISTERED':
#         registration_confirmed.set()
#         print("Регистрация на сервере выполнена успешно.")
#     elif action == 'ERROR':
#         print(f"Ошибка с сервера: {message.get('message')}")
#     elif action == 'FILE':
#         await process_incoming_file(message, addr)
#     # elif action == 'CONFIRM_FILE_PART':
#     #     file_id = message['file_id']
#     #     part_number = message['part']
#     #     if file_id in file_parts_storage:
#     #         file_parts_storage[file_id]['confirmed_parts'].add(part_number)
#
#
# async def process_incoming_file(message, addr):
#     global file_parts_storage
#
#     # Получение информации о части файла из сообщения
#     part_number = message['part']  # Номер текущей части файла
#     total_parts = message['total_parts']  # Общее количество частей файла
#     file_data_hex = message['data']  # Данные текущей части файла в формате шестнадцатеричной строки
#     file_id = message['file_id']  # Уникальный идентификатор файла
#     file_extension = message.get('file_extension',
#                                  '.data')  # Получение расширения файла из сообщения, по умолчанию '.data'
#
#     # Преобразование шестнадцатеричных данных в байты
#     file_data = bytes.fromhex(file_data_hex)
#
#     # Проверка, есть ли уже запись о данном файле в хранилище частей файлов
#     if file_id not in file_parts_storage:
#         # Если записи о файле нет, создаем новую запись
#         file_parts_storage[file_id] = {'received_parts': 0, 'total_parts': total_parts, 'parts': {},
#                                        'extension': file_extension}
#
#     # Сохранение данных текущей части файла в хранилище
#     file_parts_storage[file_id]['parts'][part_number] = file_data  # Сохраняем данные текущей части файла по ее номеру
#     file_parts_storage[file_id]['received_parts'] += 1  # Увеличиваем счетчик полученных частей файла на 1
#
#     if file_id in file_parts_storage and part_number in file_parts_storage[file_id]['parts']:
#         # Отправляем подтверждение о получении части файла
#         confirmation_data = json.dumps({
#             'action': 'CONFIRM_FILE_PART',
#             'file_id': file_id,
#             'part': part_number
#         })
#         await send_udp_packet(addr[0], addr[1], confirmation_data)
#
#     # Проверка, все ли части файла получены
#     if file_parts_storage[file_id]['received_parts'] == total_parts:
#         # Если все части файла получены, вызываем функцию для сборки файла
#         assemble_file(file_id)
#     else:
#
#
#
# def assemble_file(file_id):
#     parts = file_parts_storage[file_id]['parts']
#     total_parts = file_parts_storage[file_id]['total_parts']
#     file_extension = file_parts_storage[file_id]['extension']  # Получаем расширение файла
#
#     file_path = os.path.join(base_save_path, f"received_file_{file_id}{file_extension}")  # Полный путь к файлу
#     with open(file_path, 'wb') as final_file:
#         # Отсортировываем номера частей и записываем их содержимое в правильном порядке
#         for i in sorted(parts.keys()):
#             final_file.write(parts[i])
#
#     print(f"Файл {file_id} успешно обработан. Сохранено по пути: {file_path}")
#     del file_parts_storage[file_id]
#
#
# async def send_file(filename, user_id):
#     file_id = str(uuid.uuid4())
#     ip, port = None
#     file_extension = os.path.splitext(filename)[1]  # Получаем расширение файла
#     for client in clients:
#         if client['client_id'] == user_id:
#             ip, port = client['ip'], client['port']
#             break
#
#     if ip and port:
#         with open(filename, 'rb') as file:
#             file_data = file.read()
#
#         chunk_size = 2048
#         chunks = [file_data[i:i + chunk_size] for i in range(0, len(file_data), chunk_size)]
#
#         # chunks = []
#         # for i in range(0, len(file_data), chunk_size):
#         #     chunk = file_data[i:i + chunk_size]
#         #     chunks.append(chunk)
#
#         for i, chunk in enumerate(chunks):
#             data = json.dumps({
#                 'action': 'FILE',
#                 'file_id': file_id,
#                 'part': i,
#                 'total_parts': len(chunks),
#                 'data': chunk.hex(),
#                 'file_extension': file_extension  # Добавляем информацию о расширении файла
#             })
#             await send_udp_packet(ip, port, data)
#         asyncio.create_task(check_and_request_missing_parts(file_id))
#
# async def check_and_request_missing_parts(file_id):
#     await asyncio.sleep(10)  # Даем время на получение подтверждений
#     missing_parts = set(range(file_send_status[file_id]['total_parts'])) - file_send_status[file_id]['confirmed_parts']
#     if missing_parts:
#         for part_number in missing_parts:
#             request_data = json.dumps({
#                 'action': 'REQUEST_FILE_PART',
#                 'file_id': file_id,
#                 'part': part_number
#             })
#             await send_udp_packet(file_send_status[file_id]['ip'], file_send_status[file_id]['port'], request_data)
#     else:
#         print(f"Все части файла {file_id} успешно доставлены.")
#
# async def get_clients(interval):
#     """Периодический запрос списка клиентов."""
#     while True:
#         data = {"action": "GET", "client_id": client_id, "src_port": src_port}
#         await send_udp_packet(server_ip, server_port, data)
#         await asyncio.sleep(interval)
#
#
# def connection_status(ip, port):
#     key = (ip, port)
#     return connection_statuses.get(key, {"status": "не найден", "last_active": 0})["status"]
#
#
# async def update_connection_status(ip, port, status):
#     """Асинхронное обновление статуса соединения."""
#     key = (ip, port)
#     connection_statuses[key] = {"status": status, "last_active": time.time()}
#     print(f"Статус подключения обновлен для {ip}:{port} до {status}")
#
#
# async def check_connections_periodically(interval):
#     """Асинхронная проверка статуса соединений и отправка heartbeat."""
#     while True:
#         current_time = time.time()
#         for key, value in list(connection_statuses.items()):
#             ip, port = key
#             # Если соединение потеряно, пропускаем
#             if value["status"] == "lost":
#                 continue
#             # Если последняя активность была давно, обновляем статус на "lost"
#             if value["status"] == "confirmed" and current_time - value["last_active"] > 10:
#                 print(f"Соединение с {ip}:{port} считается потеряным")
#                 connection_statuses[key]["status"] = "lost"  # Прямое обновление статуса
#             # Отправляем heartbeat всем подтверждённым соединениям
#             elif value["status"] == "confirmed":
#                 await send_udp_packet(ip, port, {"action": "HEARTBEAT", "message": "Heartbeat"})
#         await asyncio.sleep(interval)
#
#
# async def register_with_server(retry_attempts=3, retry_interval=7):
#     global registration_confirmed
#     for attempt in range(retry_attempts):
#         print(f"Попытка {attempt + 1} подключиться к серверу...")
#         data = {"action": "REGISTER", "client_id": client_id}
#         await send_udp_packet(server_ip, server_port, data)
#
#         try:
#             await asyncio.wait_for(registration_confirmed.wait(), timeout=retry_interval)
#             return True
#         except asyncio.TimeoutError:
#             print(f"Не удалось подключиться к серверу после попытки {attempt + 1}. Повторная попытка...")
#
#     print("Не удалось зарегистрироваться на сервере после нескольких попыток.")
#     return False
#
#
#
# import sys
# from PyQt5.QtWidgets import QMessageBox, QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QListWidget, \
#     QAction, QMenu, QFileDialog, QListWidgetItem
# from PyQt5.QtCore import QTimer, pyqtSignal, Qt
# import threading
#
#
# ########################## GUI ############################
# class AsyncioGUI(QMainWindow):
#     # Определение сигнала для запуска таймера
#     start_timer_signal = pyqtSignal(int)
#
#     def __init__(self, loop, *args, **kwargs):
#
#         super().__init__(*args, **kwargs)
#         self.loop = loop
#         self.setWindowTitle("AetherWaves")
#         self.setGeometry(100, 100, 400, 400)
#         self.connected = False  # Добавляем атрибут для отслеживания состояния подключения
#
#         self.central_widget = QWidget()
#         self.layout = QVBoxLayout(self.central_widget)
#
#         self.connect_button = QPushButton("Connect", self)
#         self.connect_button.clicked.connect(self.on_connect_or_disconnect)
#         self.layout.addWidget(self.connect_button)
#
#         self.clients_listbox = QListWidget(self)
#         self.layout.addWidget(self.clients_listbox)
#
#         self.clients_listbox.setContextMenuPolicy(Qt.CustomContextMenu)
#         self.clients_listbox.customContextMenuRequested.connect(self.show_context_menu)
#
#         self.setCentralWidget(self.central_widget)
#
#         self.timer = QTimer(self)
#         # Подключение сигнала к слоту для установки таймера
#         self.start_timer_signal.connect(self.start_timer)
#
#     # Метод для установки таймера
#     def start_timer(self, interval):
#         self.timer.timeout.connect(self.update_clients_listbox)
#         self.timer.start(interval)
#
#     def on_connect_or_disconnect(self):
#         if not self.connected:
#             asyncio.run_coroutine_threadsafe(self.connect(), self.loop)
#         else:
#             asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)
#
#     async def connect(self):
#         asyncio.run_coroutine_threadsafe(listen_for_incoming_messages('0.0.0.0', src_port), self.loop)
#         registration_success = await register_with_server()
#         if registration_success:
#             self.start_timer_signal.emit(1000)
#             self.connected = True
#             self.connect_button.setStyleSheet("background-color: green;")
#             self.connect_button.setText("Disconnect")
#             self.show_message("Connected", "Successfully connected to the server!")
#             asyncio.run_coroutine_threadsafe(get_clients(10), self.loop)
#             asyncio.run_coroutine_threadsafe(check_connections_periodically(10), self.loop)
#         else:
#             self.show_message("Connection Failed", "Could not connect to the server.")
#
#     async def disconnect(self):
#         # Здесь код для отключения от сервера
#         self.timer.stop()
#         self.clients_listbox.clear()
#         self.connected = False
#         self.connect_button.setStyleSheet("")
#         self.connect_button.setText("Connect")
#         self.show_message("Disconnected", "You have been disconnected from the server.")
#         # вот тут нужно остановить данные методы
#         self.tasks = asyncio.all_tasks(self.loop)
#
#         for task in self.tasks:
#             task.cancel()
#
#         await asyncio.gather(*self.tasks, return_exceptions=True)
#
#         # Очищаем список задач после отмены
#         self.tasks.clear()
#         self.timer.stop()
#
#     def update_clients_listbox(self):
#         self.clients_listbox.clear()
#         for client in clients:  # Предполагается, что 'clients' - это список словарей с данными клиентов
#             status = connection_statuses.get((client['ip'], client['port']), {}).get("status")
#             item_text = f"{client['client_id']} - {status}"  # Пример формирования текста элемента
#             user_id = client['client_id']  # Получаем user_id клиента из данных
#             item = QListWidgetItem(item_text)
#             item.setData(Qt.UserRole, user_id)
#             self.clients_listbox.addItem(item)
#
#     def show_message(self, title, message):
#         QMessageBox.information(self, title, message)
#
#     def show_context_menu(self, position):
#         # Получаем модельный индекс элемента под курсором мыши
#         index = self.clients_listbox.indexAt(position)
#         if index.isValid():
#             item = self.clients_listbox.item(index.row())
#             user_id = item.data(Qt.UserRole)
#             context_menu = QMenu(self)
#             # Создаем действие "Отправить файл"
#             send_file_action = QAction("Отправить файл", self)
#             # Используем lambda для передачи user_id в слот
#             send_file_action.triggered.connect(lambda: self.on_send_file_triggered(user_id))
#             # Добавляем действие в контекстное меню
#             context_menu.addAction(send_file_action)
#             # Отображаем контекстное меню в текущей позиции курсора
#             context_menu.exec_(self.clients_listbox.viewport().mapToGlobal(position))
#
#         # Показываем контекстное меню
#         context_menu.exec_(self.clients_listbox.viewport().mapToGlobal(position))
#         print(f"Клиент которому пытаюсь отправить файл {user_id}")
#
#     def on_send_file_triggered(self, user_id):
#         # Открываем файловый менеджер для выбора файла
#         filename, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Все файлы (*)")
#
#         if filename:
#             asyncio.run_coroutine_threadsafe(send_file(filename, user_id), self.loop)
#             # Здесь код для отправки файла
#             print(f"Выбран файл '{filename}' для отправки клиенту '{user_id}'")
#             # Вместо print используйте вашу логику для отправки файла
#
#
# def start_asyncio_loop(loop):
#     asyncio.set_event_loop(loop)
#     loop.run_forever()
#
#
# def main():
#     global app
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#
#     asyncio_thread = threading.Thread(target=start_asyncio_loop, args=(loop,), daemon=True)
#     asyncio_thread.start()
#
#     app = QApplication(sys.argv)
#     gui = AsyncioGUI(loop)
#
#     gui.show()
#
#     sys.exit(app.exec_())
#
#
# if __name__ == "__main__":
#     main()
