import serial
import time

ser = serial.Serial(
        # Serial Port to read the data from
        port='/dev/serial0',
 
        #Rate at which the information is shared to the communication channel
        baudrate = 9600,
   
        #Applying Parity Checking (none in this case)
        parity=serial.PARITY_NONE,
 
       # Pattern of Bits to be read
        stopbits=serial.STOPBITS_ONE,
     
        # Total number of bits to be read
        bytesize=serial.EIGHTBITS,
 
        # Number of serial commands to accept before timing out
        timeout=1
)
# Pause the program for 1 second to avoid overworking the serial port
i = 0
buffer = b''
last_received = ''
ser.flushInput()
while 1:
        i=i+1
        buffer += ser.read()
        if (b'\r\n' in buffer):
            last_received, buffer = buffer.split(b'\r\n')[-2:]
            print (last_received)
            i = 0
        if i > 1000:
             buffer = b''
             ser.flushInput()
             i = 0
             ser.sendBreak(duration = 0.02)
             time.sleep(0.2)
             ser.close()
             time.sleep(0.2)
             ser.open()
        time.sleep(0.001)

