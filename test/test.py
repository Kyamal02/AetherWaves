from scapy.all import *
from scapy.layers.inet import IP, UDP

def send_udp_packet_to_router(dst_ip, dst_port, src_port=9999):
    packet = IP(dst=dst_ip) / UDP(sport=src_port, dport=dst_port) / Raw(load="Packet for connection test")
    send(packet)
    print(f"Sent UDP packet from port {src_port} to router {dst_ip}:{dst_port}")

if __name__ == "__main__":
    router_ip = "213.234.11.2"  # Замените на IP-адрес роутера клиента
    router_port = 12345  # Замените на порт, на который необходимо отправить пакет (используйте разрешенный порт)
    send_udp_packet_to_router(dst_ip=router_ip, dst_port=router_port)
