import socket
from scapy.all import send
from scapy.layers.inet import IP, UDP


def udp_server(host='213.234.20.2', port=9999):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        print(f'Server listening on UDP port {port}...')

        while True:
            data, addr = s.recvfrom(1024)  # buffer size is 1024 bytes
            print(f'Received message: {data.decode()} from {addr}')

            # Создаем ответный пакет с Scapy
            response_packet = IP(dst=addr[0]) / UDP(sport=port, dport=addr[1]) / "Hello from server via Scapy!"
            send(response_packet)  # Отправляем пакет

if __name__ == "__main__":
    udp_server()
