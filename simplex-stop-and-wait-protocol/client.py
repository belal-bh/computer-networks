import socket
import protocol

HEAD = protocol.HEAD
TAIL = protocol.TAIL
DISCONNECT_MESSAGE = '!DISCONNECT'

client = protocol.Client()
client.connect()

try:
    PKT_BUFFER = int(input("Enter packet buffer size: "))
except:
    PKT_BUFFER = 10
first_acknowledgement = str(PKT_BUFFER)
client.send(first_acknowledgement)

packet = protocol.Packet(PKT_BUFFER)

message = "Hello, I am a client. I am sending this message. Happy coding!"
packet.append_msg(message)

active = True
while active:
    # input()
    buffer = protocol.from_network_layer(packet)
    if buffer == None:
        print(f"[NOTE] No more message left.")
        more_msg = input("Enter new message to send OR press ENTER to DISCONNECT: ")
        if more_msg:
            packet.append_msg(more_msg)
            continue
        active = False
        continue
    frame = protocol.Frame(frame_kind='data', head=HEAD, tail=TAIL, packet=buffer)
    protocol.to_physical_layer(frame, client)
    protocol.wait_for_event(event=client, t=2)
    print()

client.send(DISCONNECT_MESSAGE)