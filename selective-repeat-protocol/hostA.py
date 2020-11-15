from protocol import Server

host_a = Server(port=9999, client_receiver_port=9998)

host_a.start()