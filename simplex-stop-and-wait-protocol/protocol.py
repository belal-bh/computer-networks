import socket 
import threading
import time

HEAD = '1001'
TAIL = '011'
MAX_PKT = 64

class Server:
    def __init__(self, host=None, port=None, header=MAX_PKT, msg_format='utf-8', disconnect_msg='!DISCONNECT'):
        if host == None:
            self.HOST = socket.gethostbyname(socket.gethostname())
        else:
            self.HOST = host
        if port == None:
            self.PORT = 5050
        else:
            self.PORT = port
        self.ADDRESS = (self.HOST, self.PORT)
        self.HEADER = header
        self.FORMAT = msg_format
        self.DISCONNECT_MESSAGE = disconnect_msg
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def bind(self):
        print(f"[BINDING] Server is binding on {self.ADDRESS}")
        self.server.bind(self.ADDRESS)
    
    def listen(self):
        print(f"[LISTENING] Server is listening on {self.ADDRESS}")
        self.server.listen()

    def handle_client(self, conn, addr):
        print(f"[NEW CONNECTION] {addr} connected.")
        PKT_BUFFER = None
        first_msg = True
        FRAME_LENGTH = len(HEAD)+ len(TAIL)

        connected = True
        try:
            while connected:
                if first_msg:
                    buff_length = conn.recv(MAX_PKT).decode(self.FORMAT)
                    if buff_length:
                        PKT_BUFFER = int(buff_length)
                        FRAME_LENGTH += PKT_BUFFER
                        first_msg = False

                        # print(f"PKT_BUFFER={PKT_BUFFER}")

                        # continue
                frame = from_physical_layer(conn, FRAME_LENGTH, self.FORMAT) #conn.recv(FRAME_LENGTH).decode(self.FORMAT)
                msg = frame[len(HEAD): - len(TAIL)]
                if msg == self.DISCONNECT_MESSAGE:
                    connected = False
                    continue

                # print(f"[{addr}] {frame}")
                print(f"[{addr}] {msg}")
                to_network_layer(msg)
                conn.send("Msg received".encode(self.FORMAT))
                print()
        except:
            pass


    def start(self):
        self.bind()
        self.listen()

        try:
            while True:
                conn, addr = self.server.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.start()

                print(f"[ACTIVE CONNECTION] {threading.activeCount() - 1}")
        except:
            pass


class Client:
    def __init__(self, host=None, port=None, header=MAX_PKT, msg_format='utf-8'):
        if host == None:
            self.HOST = socket.gethostbyname(socket.gethostname())
        else:
            self.HOST = host
        if port == None:
            self.PORT = 5050
        else:
            self.PORT = port
        self.ADDRESS = (self.HOST, self.PORT)
        self.HEADER = header
        self.FORMAT = msg_format
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def connect(self):
        print(f"[CONNECTING] client is connecting with {self.ADDRESS}")
        self.client.connect(self.ADDRESS)

    def send(self, msg):
        message = msg.encode(self.FORMAT)
        self.client.send(message)
        # print(self.client.recv(MAX_PKT).decode(self.FORMAT))

class Packet:
    def __init__(self, packet_size, msg='', format='utf-8'):
        self.message = msg
        self.packet_size = packet_size
        self.start_index = 0
        self.FORMAT = format
    
    def append_msg(self, msg):
        self.message += msg
    
    def get_packet(self):
        if self.start_index + self.packet_size <= len(self.message):
            packet = self.message[self.start_index : self.start_index + self.packet_size]
            self.start_index = self.start_index + self.packet_size
        elif self.start_index < len(self.message):
            packet = self.message[self.start_index : len(self.message)]
            self.start_index = len(self.message)
        else:
            packet = None
            return packet

        if len(packet) < self.packet_size:
            packet += ' ' * (self.packet_size - len(packet))
        
        return packet

class Frame:
    def __init__(self, frame_kind, head, tail, packet, format='utf-8'):
        self.kind = frame_kind
        self.head = head
        self.tail = tail
        self.info = packet
        self.seq = 0
        self.ack = 0
        self.FORMAT = format

    def get_frame(self):
        frame = f"{self.head}{self.info}{self.tail}"
        return frame
    


def from_network_layer(buffer):
    """Fetch a packet from the network layer for transmission on the channel."""
    packet = buffer.get_packet()
    # print(f'buffer.message:{buffer.message}')
    # if packet == None:
    #     print(f"[from_network_layer] packet:NULL")
    print(f"[from_network_layer] packet:{packet}")
    return packet

def to_network_layer(packet):
    """Deliver information from an inbound frame to the network layer."""
    print(f"[to_network_layer] packet:{packet}")

def from_physical_layer(conn, FRAME_LENGTH, FORMAT):
    """Go get an inbound frame from the physical layer and copy it to r."""
    frame = conn.recv(FRAME_LENGTH).decode(FORMAT)
    print(f"[from_physical_layer] frame:{frame}")
    return frame

def to_physical_layer(frame, sender):
    """Pass the frame to the physical layer for transmission."""
    frame_msg = frame.get_frame()
    print(f"[to_physical_layer] frame:{frame_msg}")
    sender.send(frame_msg)

def wait_for_event(event, t):
    """Wait for an event to happen; return its type in event."""
    time.sleep(t)
