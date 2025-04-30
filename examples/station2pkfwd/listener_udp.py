# listener_udp.py
import socket

UDP_IP = "0.0.0.0"
UDP_PORT = 1680

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Escuchando en UDP {UDP_PORT}...")

while True:
    data, addr = sock.recvfrom(1024)
    print(f"Recibido de {addr}: {data.hex()}")
