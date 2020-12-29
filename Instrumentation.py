import serial

class SRS830():
    """
    Yeah, I know this is overkill. Just to keep the creation of the serial port
    and the send + recieve functions together...
    """
    def __init__(self, *args,**kwargs):
        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        # at the moment it is connected to COM?
        self.ser.port = 'COM1'
        # A timeout is sometimes nice to abort
        self.ser.timeout = 0.5
        # More settings needed for the SRS830
        self.ser.bytesize=8
        self.ser.parity='N'
        self.ser.stopbits=1
        self.ser.xonxoff=0

    def set_command(self, command):
        self.ser.open()
        self.ser.write(command)
        self.ser.close()

    def get_command(self, command):
        self.ser.open()
        self.ser.write(command)
        response = self.ser.read(15).decode()
        self.ser.close()
        return response
