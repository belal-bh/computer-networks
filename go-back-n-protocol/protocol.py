import pickle
import socket 
import threading
import time
import select
import random
import string

HEAD = '000'
TAIL = '11'
MAX_PKT = 64

class Server:
    def __init__(self, host=None, port=None, client_receiver_port=None, header=MAX_PKT, msg_format='utf-8', disconnect_msg='!DISCONNECT'):
        if host == None:
            self.HOST = socket.gethostbyname(socket.gethostname())
        else:
            self.HOST = host
        if port == None:
            self.PORT = 5050
        else:
            self.PORT = port
        if client_receiver_port == None:
            self.client_receiver_port = 5051
        else:
            self.client_receiver_port = client_receiver_port
        self.ADDRESS = (self.HOST, self.PORT)
        self.HEADER = header
        self.FORMAT = msg_format
        self.DISCONNECT_MESSAGE = disconnect_msg
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.client_receiver_address = (self.HOST, self.client_receiver_port)

        self.transmit_window = 7
        self.max_seq_num = self.transmit_window + 1
        self.receive_window = 1
        self.expected_pkt = 0
        self.frame_to_send = 0
        self.timer_duration = 1000 #in milliseconds

        self.q = Queue(self.transmit_window)
        self.time_stamp_q = Queue(self.transmit_window)
        self.tempq = Queue(self.transmit_window)

        self.packet_drop_probability = 0.05
        self.ack_drop_probability = 0.05

        self.base_time = time.time()*1000
        self.lock = threading.Lock()

    def should_drop(self, threshold) :
        temp = random.uniform(0,1)
        if(temp<=threshold) : return True
        else : return False


    def bind(self):
        print(f"{time.ctime(time.time())}\t[BINDING] Server is binding on {self.ADDRESS}")
        self.server.bind(self.ADDRESS)
    
    def listen(self):
        print(f"{time.ctime(time.time())}\t[LISTENING] Server is listening on {self.ADDRESS}")
        self.server.listen()
    
    def connect(self):
        print(f"{time.ctime(time.time())}\t[CONNECTING] host is connecting with {self.ADDRESS}")
        self.server.connect(self.ADDRESS)

    def send(self, new_packet_string, address):
        # print(f'address:{address}')
        try:
            self.server.sendto(new_packet_string, address)
            return
        except Exception as __e:
            # print(f"SEND ERROR=>{__e}")
            pass

    def respond_to_pck_resending(self, resend_pkts):
        #Resend all the buffered packets
        print(f"{time.ctime(time.time())}\tRESENDING  all the buffered packets")
        self.tempq.clear()
        self.time_stamp_q.clear()
        while (self.q.empty()==False) :
            self.tempq.put(self.q.get())
        resend_pkts.clear()

    def pkt_sender(self, resend_pkts):
        while(True):
            if(resend_pkts.is_set()) : continue
            cur_time = time.time()*1000 - self.base_time
            if(self.q.full() == False):
                if (self.tempq.empty()) :
                    # create and send packet here
                    new_packet = data_frame(self.frame_to_send % self.max_seq_num)
                    cur_time = time.time()*1000 - self.base_time

                    new_packet_string = pickle.dumps(new_packet)
                    self.q.put(new_packet) #Insert a packet into queue
                    self.time_stamp_q.put(cur_time)
                    if (self.should_drop(self.packet_drop_probability) == False) :
                        self.send(new_packet_string, self.client_receiver_address)
                        print(f"{time.ctime(time.time())}\tSENT_TO:{self.client_receiver_address}), SEQ:{new_packet.data_num}, DATA:{new_packet.data}")
                    self.frame_to_send = (self.frame_to_send + 1) % self.max_seq_num
                else :
                    #Get that pack from tempq top
                    new_packet = self.tempq.get()
                    cur_time = time.time()*1000	- self.base_time

                    new_packet_string = pickle.dumps(new_packet)
                    self.q.put(new_packet) #Insert a packet into queue
                    self.time_stamp_q.put(cur_time)
                    if (self.should_drop(self.packet_drop_probability) == False) :
                        self.send(new_packet_string, self.client_receiver_address)
                        print(f"{time.ctime(time.time())}\tSENT_TO:{self.client_receiver_address}), SEQ:{new_packet.data_num}, DATA:{new_packet.data}")
                        
                time.sleep(0.502)
                # time.sleep(0.002)


    def pkt_receiver(self, resend_pkts):
        while(True) :
            cur_time = time.time()*1000 - self.base_time
            if (self.time_stamp_q.empty() == False) :
                if abs(cur_time - self.time_stamp_q.top()) >= self.timer_duration :
                    # We should have got the acknowledgement for this packet by now
                    # Means we need to signal the timeout event
                    # logging.info ("Timeout occured at time %f, will need to resend all the packets in window" %cur_time)
                    print((f"{time.ctime(time.time())}\tTimeout occured at time {cur_time}, will need to resend all the packets in window"))
                    resend_pkts.set()
                    self.respond_to_pck_resending(resend_pkts)

            try:
                data, __address = self.server.recvfrom(65507)
                packet = pickle.loads(data)
                cur_time = time.time()*1000 - self.base_time
                if isinstance(packet, data_frame) :
                    print(f"{time.ctime(time.time())}\tRECIEVED_FROM:{__address}, FRAME=> SEQ:{packet.data_num}, DATA:{packet.data}")
                    if packet.data_num == self.expected_pkt :
                        # create and send the acknowledgement for this received packet
                        ack = ack_frame(self.expected_pkt)
                        ack_string = pickle.dumps(ack)
                        # logging.info ("sending ack for data packet - %d at time %f" %(expected_pkt, cur_time))

                        if (self.should_drop(self.ack_drop_probability) == False) :
                            # logging.info ("Success - ack for data packet - %d at time %f" %(expected_pkt, cur_time))
                            self.send(ack_string, __address)
                            print(f"{time.ctime(time.time())}\tACK_TO:{__address}, ACK=> NUM:{ack.ack_num}")
                            
                        self.expected_pkt = (self.expected_pkt + 1)% self.max_seq_num
                elif isinstance(packet, ack_frame):
                    # logging.info ("received ack for data packet - %d at time %f" %(packet.ack_num, cur_time)) 
                    print(f"{time.ctime(time.time())}\tRECIEVED_FROM:{__address}, ACK=> SEQ:{packet.ack_num}")
                    
                    self.lock.acquire()
                    while((self.q.empty()==False) and ((self.q.top()).data_num != packet.ack_num)) :
                        self.q.get()
                        self.time_stamp_q.get()
                    if ((self.q.empty()==False) and ((self.q.top()).data_num == packet.ack_num)) :
                        self.q.get()
                        self.time_stamp_q.get()
                    self.lock.release()
            except Exception as __e:
                pass
                # print(f"{time.ctime(time.time())}\tException")

    
    def start(self):
        self.bind()
        self.server.setblocking(0)

        resend_pkts = threading.Event()

        pkt_sender = threading.Thread(name='pkt_sender', 
                        target=self.pkt_sender,
                        args=[resend_pkts])
        pkt_sender.start()

        pkt_receiver = threading.Thread(name='pkt_receiver', 
                        target=self.pkt_receiver,
                        args=[resend_pkts])
        pkt_receiver.start()

        while True :
            self.lock.acquire()
            self.lock.release()
            time.sleep(10)


class Queue:
    def __init__(self, max_size):
        self.max_size = max_size
        self.list = list()

    def put(self, element):
        self.list.append(element)

    def get(self):
        temp = self.top()
        self.list.pop(0)
        return temp

    def empty(self):
        if(len(self.list) == 0):
            return True
        return False

    def full(self):
        if(len(self.list) == self.max_size):
            return True
        return False

    def top(self):
        return self.list[0]

    def clear(self):
        self.list.clear()

    def size(self) :
        return len(self.list)



class data_frame:
	def __init__(self, num):
		self.data_num = num
		self.L = random.randint(8, 16) #(64, 256)
		self.header = "0"*3   #000
        # self.tail = '11'
		self.check_sum = "0"*4
		self.data = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(self.L-3)])

class ack_frame:
	def __init__(self, num):
		self.ack_num = num
		self.L = 3
		self.header = "0" * 3
		self.check_sum = "0"*4