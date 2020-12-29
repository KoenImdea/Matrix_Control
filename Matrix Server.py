"""
v1.0 Started on 16/10/2020

Author: Koen

Purpose: Control Matrix Experiments to syncronice with external instruments
Important: Code must be extendible, responsive, and allow for easy data-analysis later.

The server connects to Matrix using mate4dummies, and accepts client connections from programs that controll the external instruments.
"""
# import socket library
import socket
# import threading library
import threading
#Import tkinter for GUI and matplotlib for plots
import tkinter
#We'll make use of numpy
import numpy as np
# Time keeping and sleeping
import time
# Commands to Matrix will need to be queued so as to only open up one connection.
import queue
# And off course mate 4 dummies to talk to Matrix
import mate4dummies.objects as mo
import custom_MATE_for_Dummies
#for testing purposes
import random
import quick_tests
import select



"""We use a primary thread that will kick off the GUI and subthreads to keep everything separated. This is needed due to the asyncronous calls to Matrix/Serial ports, and to keep the GUI responsive while waiting for external updates."""


class ThreadedClient:
    """
    Launch the main part of the GUI and the worker thread. periodicCall and
    endApplication could reside in the GUI part, but putting them here
    means that you have all the thread controls in a single place.
    """
    def __init__(self, master):
        """
        Start the GUI and the asynchronous threads. We are in the main
        (original) thread of the application, which will later be used by
        the GUI as well. We spawn a new thread for the worker (I/O).
        """
        self.master = master

        """
        Prepare the Server to acceps connections.
        """
        # Choose a port that is free
        self.port = 5000
        # server is on localhost
        self.ip = "127.0.0.1"
        # Address is stored as a tuple
        self.address = (self.ip, self.port)
        # the format in which encoding
        # and decoding will occur
        self.format = "utf-8"
        # Lists that will contains
        # all the clients connected to
        # the server and their names.
        self.clients = {}
        # Create a new socket for
        # the server
        self.server = socket.socket(socket.AF_INET,
                               socket.SOCK_STREAM)

        # bind the address of the
        # server to the socket
        self.server.settimeout(2)

        self.server.bind(self.address)

        self.ClientCommunication = threading.Thread(target=self.ClientThread)
        self.accepting = True
        self.ClientCommunication.start()


        # Create the queue
        self.queue = queue.Queue()



        # Set up the GUI part
        self.gui = ServerWindow(master, self.queue, self.connect, self.sendmessage, self.clients)
        root.connected = 0
        # Set up the thread to do asynchronous I/O
        # More threads can also be created and used, if necessary

    def connect(self, value):
        if value == 1:
            root.connected = 1
            self.MatrixCommunication = threading.Thread(target=self.MatrixThread)
            self.MatrixCommunication.start()

            # Start the periodic call in the GUI to check if the queue contains
            # anything
            self.periodicCall()
        else:

            root.connected = 0


    #THIS NEEDS TO CHANGE
    def periodicCall(self):
        """
        Check every 200 ms if there is something new in the queue.
        """
        #self.gui.processIncoming()
        if not root.connected:
            pass
        else:
            self.master.after(200, self.periodicCall)

    #THIS NEEDS TO CHANGE
    def MatrixThread(self):
        """
        This is where we handle the asynchronous I/O. For example, it may be
        a 'select(  )'. One important thing to remember is that the thread has
        to yield control pretty regularly, by select or otherwise.
        """
        while root.connected or (not self.queue.empty()):
            # To simulate asynchronous I/O, we create a random number at
            # random intervals. Replace the following two lines with the real
            # thing.
            while self.queue.qsize():
                try:
                    root.in_progress.acquire(blocking=True, timeout=-1)

                    item = self.queue.get(0)
                    # Check contents of message and do whatever is needed. As a
                    # simple test, print it (in real life, you would
                    # suitably update the GUI's display in a richer fashion).
                    print(item)
                    answer = eval("Faker." + item[0])
                    if not(answer == "Acknowledged"):
                        root.connected = 0
                        self.gui.connectCommand(0)

                        self.gui.console["text"] = "Connect to \n Matrix"

                    print(answer)
                    time.sleep(0.2)
                    root.in_progress.release()
                except self.queue.empty():
                    # just on general principles, although we don't
                    # expect this branch to be taken in this case
                    pass
            time.sleep(0.2)
        self.gui.console["text"] = "Connect to \n Matrix"


    def ClientThread(self):
        print("server is working on " + self.ip)

        # listening for connections

        self.server.listen()

        while self.accepting:

            # accept connections and returns
            # a new connection to the client
            #  and  the address bound to it
             try:
                conn, addr =  self.server.accept()
                conn.send("NAME".encode(self.format))

                # 1024 represents the max amount
                # of data that can be received (bytes)
                name = conn.recv(1024).decode(self.format)

                # append the name and client
                # to the respective list

                self.clients[conn] = name
                self.cleanup()
                print(f"Name is :{name}")

                conn.send('Connection successful!'.encode(self.format))

                # Start the handling thread
                thread = threading.Thread(target = self.handle,
                                          args = (conn, addr))
                thread.start()

                # no. of clients connected
                # to the server
                print(f"active connections {threading.activeCount()-1}")


             except socket.timeout:
                pass

        self.server.close()




    def handle(self, conn, addr):

        print(f"new connection {addr}")
        self.clientconnected = True
        while self.clientconnected:

            # See if the socket is marked as having data ready.
            r, w, e = select.select((conn,), (), (), 0)
            if r:
                # recieve message
                message = conn.recv(1024).decode(self.format)
                # Length of zero ==> connection closed.
                if len(message) == 0:
                    # close the connection
                    conn.close()
                    del self.clients[conn]
                    if conn in root.add_param.keys():
                        for i in root.add_param[conn]:
                            self.queue.put(["remove_parameter(\"" + i + "\")" , "master"])
                        del root.add_param[conn]
                    self.cleanup()
                    break

                else:

                    if message == "Matrix?":
                        if root.connected:
                            self.sendmessage(conn, "Matrix Yes")
                        else:
                            self.sendmessage(conn, "Matrix No")
                    elif message[0:9] == "Parameter":
                        if conn in root.add_param.keys():
                            root.add_param[conn].append(message[message.find(":")+2:])
                        else:
                            root.add_param[conn] = [message[message.find(":")+2:]]


                    else:
                        # put message in queue for handling
                        self.queue.put((message, conn))

    def sendmessage(self, conn, message):
        while True:

            conn.send(message.encode(self.format))
            break





    def cleanup(self):
        self.gui.listbox.delete(0, tkinter.END)
        for key in self.clients.keys():
            self.gui.listbox.insert(tkinter.END, self.clients[key])
        print("Cleanup")

    def remove_parameters(self):
        pass





    def endApplication(self):
        root.update_idletasks
        #remove all additional parameters
        #close all connections
        for conn in root.add_param.keys():
            for i in root.add_param[conn]:
                self.queue.put(["remove_parameter(\"" + i + "\")" , "master"])
            del root.add_param[conn]

        self.clientconnected = False

        #Destroy all threads
        self.accepting = False
        #self.server.close()
        #socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect( (self.ip, self.port))

        if root.connected:
            self.gui.connection()
        self.master.destroy()


"""Now we define the GUI parts, starting with the main window """
class ServerWindow:
    """
    Here we create the main window when opening op the program. It is
    supposed to be modular and easily extendible.
    """
    def __init__(self, master, queue, connectCommand, sendmessage, clients):
        self.queue = queue
        # Set up the GUI
        self.connectCommand = connectCommand
        self.sendmessage = sendmessage
        self.master = master
        self.clients = clients
        self.master.resizable(False, False)
        # First block is the Code to allow to connect to Matrix
        self.ConnectFrame = tkinter.Frame(master, height = 200, width = 300)
        self.console = tkinter.Button(self.ConnectFrame, text='Connect to \n Matrix',
            command=self.connection)
        self.console.pack(side="top")
        self.listbox = tkinter.Listbox(self.ConnectFrame)
        self.listbox.pack(side="bottom", fill=tkinter.Y)
        self.ConnectFrame.pack(side = "top")
        self.ConnectFrame.propagate(0)


        # Add more GUI stuff here depending on your specific needs
        #.protocol("WM_DELETE_WINDOW", self.endCommand()


    def processIncoming(self, command, caller):
        """Here we place Matrix commands in the queue."""
        item = [command, caller]
        self.queue.put(item)



    def connection(self):
        """Connect to, and disconnect from Matrix
            Meanwhile, update the available options.

        """
        if root.connected == 0:
            answer = Faker.connect()
            print(answer)
            if answer == "Acknowledged":
                self.connectCommand(1)
                for key in self.clients.keys():
                    self.sendmessage(key, "Matrix Yes")
                self.console["text"] = "Disconnect from \n Matrix"
            else:
                for key in self.clients.keys():
                    self.sendmessage(key, "Matrix No")
                print("Error")

        else:
            for key in self.clients.keys():
                self.sendmessage(key, "Matrix No")
            while not (list(root.add_param.keys()) == []):
                conn = list(root.add_param.keys())[0]
                for i in root.add_param[conn]:
                    self.queue.put(["remove_parameter(\"" + i + "\")" , "master"])
                del root.add_param[conn]
            print("I pass by here")
            self.queue.put(["disconnect()" , "master"])


            self.connectCommand(0)







rand = random.Random()
root = tkinter.Tk()
root.in_progress = threading.RLock()
root.add_param = {}
root.in_progress = threading.RLock()
Faker = quick_tests.FAKE_MATRIX()

#client = tkinter.Toplevel()
#client.title("Matrix Conection Client")
Instance = ThreadedClient(root)
#print(dir(client))
root.wm_protocol("WM_DELETE_WINDOW", lambda: Instance.endApplication())
root.mainloop()
