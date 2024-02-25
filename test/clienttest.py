from scapy.all import send
from scapy.layers.inet import IP, UDP
import random

import socket

def send_udp_packet(dst_ip, dst_port, src_port, message="Hello from client via Scapy!"):
    packet = IP(dst=dst_ip) / UDP(sport=src_port, dport=dst_port) / message
    send(packet)  # Отправляем пакет

def listen_for_response(src_port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("0.0.0.0", src_port))
        data, addr = s.recvfrom(1024)
        print(f"Received response: {data.decode()}")

if __name__ == "__main__":
    src_port = random.randint(1024, 65535)  # Пример порта клиента
    send_udp_packet("213.234.20.2", 9999, src_port)
    listen_for_response(src_port)
