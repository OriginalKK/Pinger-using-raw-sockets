Ping implementation using raw sockets in python. 

Checks if the destination address is valid. If it is then it packs the current time into a packet, computes the checksum and sends the 
packet to the destination address. If a response is received, then the response packet is unpacked and the RTT is computed by getting
the data from the packet. The socket is closed at every iteration. 
