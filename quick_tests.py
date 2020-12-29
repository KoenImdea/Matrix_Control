from time import sleep
import random
import socket
import threading
import tkinter


class FAKE_SRS830:
    def __init__(self, *args,**kwargs):
        self.oflt = 6
        self.freq = 666.00
        self.sens = 25
        self.harm = 1
        self.slvl = 0.202
        self.phas = 40.2

    def set_command(self, command):
        if command[0:4] == "SENS":
            self.sens = int(command[4:])
            print(self.sens)
        elif command[0:4] == "PHAS":
            self.phas = float(command[4:])
            print(self.phas)
        elif command[0:4] == "FREQ":
            self.freq = float(command[4:])
            print(self.freq)
        elif command[0:4] == "HARM":
            self.harm = int(command[4:])
            print(self.harm)
        elif command[0:4] == "SLVL":
            self.slvl = float(command[4:])
            print(self.slvl)
        elif command[0:4] == "OFLT":
            self.oflt = int(command[4:])
            print(self.oflt)

    def get_command(self, command):
        sleep(0.4)
        if command[0:4] == "SENS":
            return "{:02}".format(self.sens)
        elif command[0:4] == "PHAS":
            return "{:06.2f}".format(self.phas)
        elif command[0:4] == "FREQ":
            return "{:06.2f}".format(self.freq)
        elif command[0:4] == "HARM":
            return "{:02}".format(self.harm)
        elif command[0:4] == "SLVL":
            return "{:05.3f}".format(self.slvl)
        elif command[0:4] == "OFLT":
            return "{:02}".format(self.oflt)

class FAKE_MATRIX:
    def __init__(self, *args,**kwargs):
        self.connected = 0
        self.parameters = {}
        self.rand = random.Random()


    def add_additional_parameter(self, name, value, unit, type):
        response_time = 100 + (self.rand.random()*100)
        sleep(response_time/1000)
        if name in self.parameters.keys():
            self.connected = 0
            return "Error"
        else:
            self.parameters[name] = [value, unit, type]
            print("Parameter " + name + " added.")
            return "Acknowledged"

    def parameter_set(self, name, value):
        response_time = 100 + (self.rand.random()*100)
        sleep(response_time/1000)
        if name in self.parameters.keys():
            self.parameters[name][0] = value
            print(name + ": " + str(value) + " " + str(self.parameters[name][1]))
            return "Acknowledged"
        else:
            self.connected = 0
            return "Error"

    def remove_parameter(self, name):
        response_time = 100 + (self.rand.random()*100)
        sleep(response_time/1000)
        if name in self.parameters.keys():
            del self.parameters[name]
            print("Parameter " + name + " removed.")
            return "Acknowledged"
        else:
            self.connected = 0
            return "Error"

    def connect(self):
        response_time = 100 + (self.rand.random()*100)
        sleep(response_time/1000)
        self.connected = 1
        return "Acknowledged"

    def disconnect(self):
        response_time = 100 + (self.rand.random()*100)
        sleep(response_time/1000)
        if self.parameters != {}:
            print("You blithering idiot")
            for key in self.parameters.keys():
                print(key)
        self.connected = 0
        return "Acknowledged"

class FAKE_LS325:
    def get_command(self, command):
        sleep(0.4)
        if command[0:5] == "KRDG?":
            rand = random.Random()
            return 4.3 + (rand.random()/100)

"""
import threading
import time
in_progress = threading.RLock()

def dumb_frunction(a, start):
    in_progress.acquire(blocking=True, timeout=-1)

    time.sleep(2)
    stop = time.perf_counter()
    print(a)
    print(start)
    print(stop - start)
    in_progress.release()

start = time.perf_counter()

Push_Settings = threading.Thread(target=dumb_frunction, args=("KK", start))
#in_progress.clear

Push_Settings.start()
#in_progress.set
print("Now")
print("How Long?")
start = time.perf_counter()

Push_Settings = threading.Thread(target=dumb_frunction, args=("KK2",start))

Push_Settings.start()
print("Finished!")
"""
class ClientTemplate:
    def __init__(self):
            self.port = 5000
            self.server = "127.0.0.1"
            self.address = (self.server, self.port)
            self.format = "utf-8"

            # Create a new client socket
            # and connect to the server
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect(self.address)
            self.client.settimeout(10)
            rcv = threading.Thread(target=self.receive)
            rcv.start()


    def receive(self):
        while True:
            try:
                message = self.client.recv(1024).decode(self.format)

                # if the messages from the server is NAME send the client's name
                if message == 'NAME':
                    self.client.send("Testing".encode(self.format))
                else:
                    print(message)
            except:
                # an error will be printed on the command line or console if there's an error
                print("An error occured!")
                self.client.close()
                break

    def sendMessage(self):
        while True:

            self.client.send(message.encode(self.format))
            break

    def goAhead(self, name):
        # the thread to receive messages
        rcv = threading.Thread(target=self.receive)
        rcv.start()
#client = ClientTemplate()
#client2 = ClientTemplate()
