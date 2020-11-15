from protocol import Server

host_b = Server(port=9998, client_receiver_port=9999)

host_b.start()