"""
This file will handle all comunication to SRS830 lock-in
v0.3 started on 19/10/2020
"""
# tkinter for the GUI
import tkinter
import threading
import quick_tests
import Instrumentation as inst
import select
import socket
from time import sleep


lockin = quick_tests.FAKE_SRS830()
#lockin = inst.SRS830()

# initialize some constants
sensitivities = {0: "2 nV/fA", 1 : "5 nV/fA",  2 : "10 nV/fA", 3 : "20 nV/fA", 4 : "50 nV/fA",
    5 : "100 nV/fA",  6 : "200 nV/fA", 7 : "500 nV/fA", 8 : "1 μV/pA", 9 : "2 μV/pA",
    10 : "5 μV/pA", 11 : "10 μV/pA", 12 : "20 μV/pA", 13 : "50 μV/pA", 14 : "100 μV/pA" ,
    15 : "200 μV/pA", 16 : "500 μV/pA", 17 : "1 mV/nA", 18: "2 mV/nA", 19: "5 mV/nA",
    20 : "10 mV/nA", 21 : "20 mV/nA", 22: "50 mV/nA", 23: "100 mV/nA", 24 : "200 mV/nA",
    25 : "500 mV/nA", 26 : "1 V/μA"}

time_constants = {0 : "10 μs", 1 : "30 μs", 2 : "100 μs", 3 : "300 μs", 4 : "1 ms",
    5 : "3 ms", 6 : "10 ms", 7 : "30 ms", 8 : "100 ms", 9 : "300 ms", 10 : "1 s",
    11 : "3 s", 12 : "10 s", 13 : "30 s", 14 : "100 s", 15 : "300 s", 16 : "1 ks",
    17 : "3 ks", 18 : "10 ks", 19 : "30 ks"}

recomendations = """For STS: \n T1 and T2 should be large enough to not have an artifact at
    the beginning of the spectrum. Safe should be T1, T2 > 10* Time Constant (Tc).

    Time per point should be larger than Tc, and may be as large as 3*Tc.
    If time per point is > 3*Tc, you should think about increasing Tc.

    T3 and T4 can be kept shorter. You just need to leave enough time for the system
    to relax.

    Typical values for "Quick" spectroscopy: T1=T2= 100 ms, Tc = 10 ms, Time_per_point = 12 ms.
    For nice spectroscopy: check spectroscopy in nc-AFM PPT by Koen on the NAS
    It is located in: NanoChemistry/nc-AFM

    For LDOS Maps:
    Current should be larger than 40 pA.
    Enable Vext
    Traster of image should be larger than Tc of Lock-in.
    Also, lower the STM gain to 1.

    Quick and noisy LDOS map: Traster = Tc = 3 ms
    Nicer LDOS map: Traster = 12 ms, Tc = 10 ms

    NOTE: After loading settings, they are not automatically send to lock-in/Matrix.
    You need to manually Push the settings.
    """


# Create the GUI
class LockInWindow:
    """
    This will be pretty basic. Lockin only needs a few controls, a read and an apply Button.
    I'm also going to include a File menu to Load/Save parameters, and a help menu to give
    recomended values.
    """
    def __init__(self, master, *args,**kwargs):
        self.paramdict = {}
        self.master = master
        self.Matrix = False
        self.Server = False
        self.ConnectionLost = True
        self.shutdown = False
        self.port = 5000
        self.server = "127.0.0.1"
        self.address = (self.server, self.port)
        self.format = "utf-8"

        # Create a new client socket

        self.buttonpressed = 0

        # Create the classical menu
        self.Menu = tkinter.Menu(self.master)
        self.master.config(menu=self.Menu)
        #Create File menu, which contains load and Save
        self.FileMenu = tkinter.Menu(self.Menu, tearoff=0)
        self.Menu.add_cascade(label="File", menu=self.FileMenu)
        self.FileMenu.add_command(label="Load Settings", command=self.loadsettings)
        self.FileMenu.add_command(label="Save Settings", command=self.savesettings)
        self.FileMenu.add_separator()
        self.FileMenu.add_command(label = "Quit", command = self.endApplication)

        #Create help menu for recomendations and about
        self.HelpMenu = tkinter.Menu(self.Menu, tearoff=0)
        self.Menu.add_cascade(label="Help", menu=self.HelpMenu)
        self.HelpMenu.add_command(label="Recomendations", command=self.show_recomend)
        self.HelpMenu.add_command(label="About", command=self.show_about)



        # I'm going to dump all the controls in a nice Frame.
        self.SRS830Controls = tkinter.Frame(self.master, height = 900, width = 300)

        self.Labelsans = tkinter.Label(self.SRS830Controls, text = "Sensitivity:")
        self.Labelsans.pack(side="top", fill=tkinter.X)

        self.senssi = tkinter.StringVar(master)
        self.senssi.set(sensitivities[25])
        self.OptionSens = tkinter.OptionMenu(self.SRS830Controls, self.senssi, *sensitivities.values())
        self.OptionSens.pack(side="top", fill=tkinter.X)


        self.Labeltc = tkinter.Label(self.SRS830Controls, text = "Time Constant:")
        self.Labeltc.pack(side="top", fill=tkinter.X)

        self.timec = tkinter.StringVar(master)
        self.timec.set(time_constants[6])
        self.Optiontimec = tkinter.OptionMenu(self.SRS830Controls, self.timec, *time_constants.values())
        self.Optiontimec.pack(side="top", fill=tkinter.X)



        self.LabelAmpl = tkinter.Label(self.SRS830Controls, text = "Amplitude (mV):")
        self.LabelAmpl.pack(side="top", fill=tkinter.X)
        self.SpinboxAmpl = tkinter.Spinbox(self.SRS830Controls, from_=4, to = 5000,
            format = "%04.0f", justify = "center", increment = 2)
        self.SpinboxAmpl.pack(side="top")


        self.Labelfreq = tkinter.Label(self.SRS830Controls, text = "Frequency (Hz):")
        self.Labelfreq.pack(side="top", fill=tkinter.X)
        self.Spinboxfreq = tkinter.Spinbox(self.SRS830Controls, from_=100.00, to = 999.99,
            format = "%03.2f", justify = "center", increment = 0.01)
        self.Spinboxfreq.pack(side="top")



        self.Labelphase = tkinter.Label(self.SRS830Controls, text = "Phase (Deg):")
        self.Labelphase.pack(side="top", fill=tkinter.X)
        self.Spinboxphase = tkinter.Spinbox(self.SRS830Controls, from_=-180.00, to = 180.00,
            format = "%03.2f", justify = "center", increment = 0.01)
        self.Spinboxphase.pack(side="top")



        self.Labelorder = tkinter.Label(self.SRS830Controls, text = "Order (#):")
        self.Labelorder.pack(side="top", fill=tkinter.X)
        self.Spinboxorder = tkinter.Spinbox(self.SRS830Controls, from_=1, to = 3,
            format = "%01.0f", justify = "center", increment = 1)
        self.Spinboxorder.pack(side="top")

        self.SRS830Controls.pack(side="top")

        # Now make a frame for the arcion buttons Push and Retrieve
        self.SRS830Action = tkinter.Frame(self.master, height = 900, width = 300)

        self.ButtonPush = tkinter.Button(self.SRS830Action, text='Push \n Settings',
            command=self.push)
        self.ButtonPush.pack(side = "left")

        self.ButtonPull = tkinter.Button(self.SRS830Action, text='Retrieve \n Settings',
            command=self.pull)
        self.ButtonPull.pack(side = "left")

        self.SRS830Action.pack(side="top")

        self.ConnectionServer = tkinter.Frame(self.master, height = 200, width = 300)

        self.LabelServer = tkinter.Label(self.ConnectionServer, text = "Server Connection:")
        self.LabelServer.pack(side="left")

        self.CanvasServer = tkinter.Canvas(self.ConnectionServer, width=25, height=25)
        # change fill color of the status oval
        self.StatusServer = self.CanvasServer.create_oval(5, 5, 20, 20, fill="red", tags="state")
        self.CanvasServer.pack(side = "right")

        self.ConnectionServer.pack(side = "top")

        self.ConnectionMatrix = tkinter.Frame(self.master, height = 200, width = 300)

        self.LabelMatrix = tkinter.Label(self.ConnectionMatrix, text = "Matrix Connection:")
        self.LabelMatrix.pack(side="left")

        self.CanvasMatrix = tkinter.Canvas(self.ConnectionMatrix, width=25, height=25)
        # change fill color of the status oval
        self.StatusMatrix = self.CanvasMatrix.create_oval(5, 5, 20, 20, fill="red", tags="state")
        self.CanvasMatrix.pack(side = "right")

        self.ConnectionMatrix.pack(side = "top")

        clienthelper = threading.Thread(target=self.connectionhandler)
        clienthelper.start()



    def push(self):
        """
        Push selected settings to lock-in using a extra thread to keep GUI responsive
        """
        self.slvl = float(self.SpinboxAmpl.get())/1000
        self.freq = self.Spinboxfreq.get()
        self.phas = self.Spinboxphase.get()
        self.harm = self.Spinboxorder.get()
        for key in time_constants.keys():
            if time_constants[key] == self.timec.get():
                self.oflt = int(key)
        for key in sensitivities.keys():
            if sensitivities[key] == self.senssi.get():
                self.sens = int(key)
        # Actual communication goes to a separate thread, to not block the GUI.
        self.Push_Settings = threading.Thread(target=self.pushset)
        self.Push_Settings.start()

    def pushset(self):
        # As this is a separate thread, we can wait for the slower RS232 communication.
        lockin.set_command("SENS"+str(self.sens))
        self.master.after(500, lockin.set_command("SLVL"+"{:05.3f}".format(self.slvl)+"\r"))
        self.master.after(500, lockin.set_command("FREQ"+"{:06.2f}".format(float(self.freq))+"\r"))
        self.master.after(500, lockin.set_command("PHAS"+"{:06.2f}".format(float(self.phas))+"\r"))
        self.master.after(500, lockin.set_command("HARM"+str(self.harm)))
        self.master.after(500, lockin.set_command("OFLT"+str(self.oflt)))
        if self.buttonpressed == 0:
            self.create_parameters()
            if self.Matrix:
                self.buttonpressed = 1
        else:
            self.update_parameters()


    def pull(self):
        """Pull the settings from the lock-in using a separate thread to keep the GUI responsive """
        self.Pull_Settings = threading.Thread(target=self.pullset)
        self.Pull_Settings.start()



    def pullset(self):
        # Get stuff as fast as possible and save it in local variables
        self.slvl = float(lockin.get_command("SLVL?\r"))
        self.freq = float(lockin.get_command("FREQ?\r"))
        self.phas = float(lockin.get_command("PHAS?\r"))
        self.harm = int(lockin.get_command("HARM?\r"))
        self.oflt = int(lockin.get_command("OFLT?\r"))
        self.sens = int(lockin.get_command("SENS?\r"))
        # Then update the GUI
        self.senssi.set(sensitivities[self.sens])
        self.timec.set(time_constants[self.oflt])
        self.SpinboxAmpl.delete(0, "end"); self.SpinboxAmpl.insert(0, str(int(1000*self.slvl)))
        self.Spinboxphase.delete(0, "end"); self.Spinboxphase.insert(0, str(self.phas))
        self.Spinboxfreq.delete(0, "end"); self.Spinboxfreq.insert(0, str(self.freq))
        self.Spinboxorder.delete(0, "end"); self.Spinboxorder.insert(0, str(self.harm))
        # Also send the values to Matrix
        if self.buttonpressed == 0:
            self.create_parameters()
            self.buttonpressed = 1
        else:
            self.update_parameters()

    def loadsettings(self):
        # Ask for filename
        self.filename = tkinter.filedialog.askopenfilename(filetypes=(("txt", "*.txt"),("All files", "*.*")))
        # Read the settings, and store them
        with open(self.filename, "r") as file:
            for line in file:
                if "Time Constant" in line:
                    self.oflt = int(line[line.find("=")+1:])
                elif "Sensitivity" in line:
                    self.sens = int(line[line.find("=")+1:])
                elif "Modulation" in line:
                    self.slvl = float(line[line.find("=")+1:])/1000
                elif "Frequency" in line:
                    self.freq = float(line[line.find("=")+1:])
                elif "Harmonic" in line:
                    self.harm = int(line[line.find("=")+1:])
                elif "Phase" in line:
                    self.phas = float(line[line.find("=")+1:])


        # Then update the GUI
        self.senssi.set(sensitivities[self.sens])
        self.timec.set(time_constants[self.oflt])
        self.SpinboxAmpl.delete(0, "end"); self.SpinboxAmpl.insert(0, str(int(1000*self.slvl)))
        self.Spinboxphase.delete(0, "end"); self.Spinboxphase.insert(0, str(self.phas))
        self.Spinboxfreq.delete(0, "end"); self.Spinboxfreq.insert(0, str(self.freq))
        self.Spinboxorder.delete(0, "end"); self.Spinboxorder.insert(0, str(self.harm))

    def savesettings(self):
        """File format is legacy fron LabVIEW code, but will serve nicely"""
        self.save_path = tkinter.filedialog.asksaveasfilename(filetypes=(("txt","*.txt"),("All files","*.*")))
        with open(self.save_path, "w") as par:
            par.write("[Lock-IN]\r\n")
            par.write("Time Constant = " + str(self.oflt) + "\r\n")
            par.write("Sensitivity = " + str(self.sens) + "\r\n")
            par.write("Modulation = " + str(int(1000*self.slvl)) + "\r\n")
            par.write("Frequency = " + "{:.6f}".format(self.freq) + "\r\n")
            par.write("Harmonic = " + str(self.harm) + "\r\n")
            par.write("Phase = " + "{:.6f}".format(self.phas) + "\r\n")


    def show_recomend(self):
        tkinter.messagebox.showinfo(title="Recomended Settings", message=recomendations)



    def show_about(self):
         tkinter.messagebox.showinfo(title=None, message="V1.0 \n Created by Koen Lauwaet")

    def create_parameters(self):
        """Send creation commands to Matrix, and keep track of the additional
            parameters in a dict, for later removal.

        """
        if self.Matrix:
            self.sendMessage("Parameter added: Vrms")
            sleep(.2)
            self.sendMessage("add_additional_parameter(\"Vrms\", " + str(self.slvl) +", \"V\", \"double\")")
            sleep(.2)
            self.sendMessage("Parameter added: Phase")
            sleep(.2)
            self.sendMessage("add_additional_parameter(\"Phase\", " + str(self.phas) +", \"Deg\", \"double\")")
            sleep(.2)
            self.sendMessage("Parameter added: Frequency")
            sleep(.2)
            self.sendMessage("add_additional_parameter(\"Frequency\", " + str(self.freq) +", \"Hz\", \"double\")")
            sleep(.2)
            self.sendMessage("Parameter added: Harmonic")
            sleep(.2)
            self.sendMessage("add_additional_parameter(\"Harmonic\", " + str(self.harm) +", \"#\", \"int\")")
            sleep(.2)
            self.sendMessage("Parameter added: Sensitivity")
            sleep(.2)
            self.sendMessage("add_additional_parameter(\"Sensitivity\", \"" + sensitivities[self.sens] +"\", \"arb\", \"string\")")
            sleep(.2)
            self.sendMessage("Parameter added: Time Constant")
            sleep(.2)
            self.sendMessage("add_additional_parameter(\"Time Constant\", \"" + time_constants[self.oflt] +"\", \"arb\", \"string\")")


    def update_parameters(self):
        if self.Matrix:
            """Send update commands to Matrix. """
            self.sendMessage("parameter_set(\"Vrms\", " + str(self.slvl) + ")")
            self.sendMessage("parameter_set(\"Phase\", " + str(self.phas) + ")")
            self.sendMessage("parameter_set(\"Frequency\", " + str(self.freq) + ")")
            self.sendMessage("parameter_set(\"Harmonic\", " + str(self.harm) + ")")
            self.sendMessage("parameter_set(\"Sensitivity\", \"" + sensitivities[self.sens] +"\")")
            self.sendMessage("parameter_set(\"Time Constant\", \"" + time_constants[self.oflt] +"\")")

    def endApplication(self):
        self.shutdown = True
        print(f"active connections {threading.activeCount()-1}")
        sleep(2)
        print(f"active connections {threading.activeCount()-1}")
        self.master.destroy()

    def connectionhandler(self):

        while (not self.shutdown):
            if self.ConnectionLost:
                try:
                    print("As expected")
                    self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.client.connect(self.address)
                    self.client.settimeout(2)
                    self.ConnectionLost = False
                    rcv = threading.Thread(target=self.receive)
                    rcv.start()


                except:
                    pass
            sleep(2)
            self.connectionhandler()


    def receive(self):
        while (not self.ConnectionLost) and (not self.shutdown):
            try:
                # See if the socket is marked as having data ready.
                r, w, e = select.select((self.client,), (), (), 0)
                if r:
                    # recieve message
                    message = self.client.recv(1024).decode(self.format)
                    # Length of zero ==> connection closed.
                    if len(message) == 0:
                        # close the connection
                        self.client.close()
                        print("Lost Connection")
                        self.ConnectionLost = True
                        self.Matrix = False
                        self.buttonpressed = 0
                        self.Server = False
                        self.statusupdate()
                        break
                    #print("I pass by here")
                    # if the messages from the server is NAME send the client's name
                    if message == 'NAME':
                        self.sendMessage("Lock-in Module")

                    elif message == "Connection successful!":
                        self.Server = True
                        self.statusupdate()
                        self.sendMessage("Matrix?")

                    elif message == "Matrix No":
                        self.Matrix = False
                        self.buttonpressed = 0
                        self.statusupdate()

                    elif message == "Matrix Yes":
                        self.Matrix = True
                        self.statusupdate()

                    else:
                        print(message)
            except:
                # an error will be printed on the command line or console if there's an error
                print("An error occured!")
                self.client.close()
                break

    def sendMessage(self, message):
        while True:

            self.client.send(message.encode(self.format))
            break

    def statusupdate(self):
        if self.Server:
            self.CanvasServer.itemconfig(self.StatusServer, fill = "green")
            if self.Matrix:
                self.CanvasMatrix.itemconfig(self.StatusMatrix, fill = "green")
            else:
                self.CanvasMatrix.itemconfig(self.StatusMatrix, fill = "red")
        else:
            self.Matrix = False
            self.CanvasServer.itemconfig(self.StatusServer, fill = "red")
            self.CanvasMatrix.itemconfig(self.StatusMatrix, fill = "red")




root = tkinter.Tk()

Instance = LockInWindow(root)
#print(dir(client))
root.wm_protocol("WM_DELETE_WINDOW", lambda: Instance.endApplication())
root.mainloop()
