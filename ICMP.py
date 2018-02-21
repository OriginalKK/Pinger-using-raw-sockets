from socket import *
import os
import sys
import struct
import time
import select
import binascii  

ICMP_ECHO_REQUEST = 8
packets_lost = 0
min_rtt = 1000000
max_rtt = 0
SEQ = 0

def MyChecksum(hexlist):
    """
    Compute the checksum for a hexlist.  
    """
    summ=0
    carry=0

    for i in range(0,len(hexlist),2):
        summ+=(hexlist[i]<< 8)  + hexlist[i+1]
        carry=summ>>16
        summ=(summ & 0xffff)  + carry
    while( summ != (summ & 0xffff)):
        carry=summ>>16
        summ=summ & 0xffffffff  + carry

    summ^=0xffff

    return summ
    
def receiveOnePing(mySocket, ID, timeout, destAddr, seq):
    """
    Receive a ping from the destination. Returns the RTT or -1 if the request
    timed out
    """
    timeLeft = timeout
    global min_rtt
    global max_rtt
    global packets_lost
    global SEQ
    global bytes
    
    while 1: 
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:
            packets_lost += 1       
            print("Request timed out.")
            delay = -1
            return delay

        timeReceived = time.time() 
        recPacket, addr = mySocket.recvfrom(1024)
        
        if (addr[0] == destAddr):
            ICMP_header = recPacket[20:28] #Fetch the ICMP header from the IP packet
            time_pack = recPacket[28:36]  #Fetch the data from the IP packet (time stamp)
            type, code, checkSum, packetID, SEQ = struct.unpack("bbHHh", ICMP_header) #unpack ICMP_header from received packet
            time_sent = struct.unpack("d", time_pack) #unpack data from IP packet
            delay = (timeReceived - time_sent[0])*1000 #RTT
            checksum = MyChecksum(recPacket[20:])
            
            bytes_header = recPacket[3:4]
            bytes = struct.unpack("b", bytes_header)
            
            #make sure this is an echo ping reply with the same ID and seq # we sent
            if (packetID == ID and type == 0 and code == 0 and checksum == 0 and seq == SEQ):
                if (delay < min_rtt):
                    min_rtt = delay     #Set new min RTT
                if (delay > max_rtt):
                    max_rtt = delay     #Set new max RTT
                return delay    
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            packets_lost += 1
            print("Request timed out.")
            delay = -1
            return delay
    
def sendOnePing(mySocket, destAddr, ID, seq):
    """ 
    Sends 1 ping to the destination address
    Header is type (8), code (8), checksum (16), id (16), sequence (16)
    """
    myChecksum = 0
    
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, seq)
    data = struct.pack("d", time.time())
    
    #Calculate the checksum on the data and the dummy header.
    myChecksum = MyChecksum ([i for i in header] + [i for i in data])
    
    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network  byte order
        myChecksum = htons(myChecksum) & 0xffff     
    else:
        myChecksum = htons(myChecksum)
        
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, seq)
    packet = header + data
    
    mySocket.sendto(packet, (destAddr, 1)) 
    # AF_INET address must be tuple, not str
    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.
    
    
def doOnePing(destAddr, timeout, seq): 
    """
    Makes a call to send a ping and receive a ping back
    Closes the socket and returns the RTT.
    """
    icmp = getprotobyname("icmp")

    mySocket = socket(AF_INET, SOCK_RAW, icmp)
    
    myID = os.getpid() & 0xFFFF  # Return the current process i
    sendOnePing(mySocket, destAddr, myID, seq)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr, seq)
    mySocket.close()
    return delay
    
def ping(host, howmany, timeout=1):
    """
    Main function. Checks if the host exists and does the user specified amount
    of pings. Sleeps for 1 second per ping.
    
    Outputs: Destination IP address, bytes sent, RTT, sequence number
    """
    try: 
        dest = gethostbyname(host)
    except error:
        print("\nINVALID HOST NAME")
        return 0
    print("Pinging " + dest + " using Python:")
    print("")
    pings = int(howmany)
    seq = 1
    
    while (pings != 0):
        delay = doOnePing(dest, timeout, seq)
        if (delay != -1):
            print("Reply from " + dest + ": " "Bytes: " + str(bytes[0]) + "   time = %.3f ms" % delay + "   seq # = " + str(SEQ))
        pings -= 1
        seq += 1
        time.sleep(1)
    if (packets_lost == 0): #gets rid of divide by 0 error
        perc_lost = 0
    if (packets_lost != 0):
        perc_lost = (packets_lost/int(howmany)) * 100
    received = int(howmany) - packets_lost
    print("\nPing statistics for: " + dest)
    print(" Packets: Sent = " + howmany + ", Received = " + str(received) + ", Lost = " + str(packets_lost) + " (" + str(perc_lost) +"% loss)")
    if (perc_lost != 100):   #Don't output preset min rtt and max rtt
        print("Approximate RTT in milli-seconds: ")
        print(" Minimum = %.3f ms" % min_rtt + ", Maximum = %.3f ms" % max_rtt)
        
ping(sys.argv[1],sys.argv[2])