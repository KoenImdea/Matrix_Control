"""
v1.0 Started on 31/13/2020

Author: Koen

Purpose: Create easy launcher for custom drift-corrected measurements.
Important: Code must be re-uable for other custom experiments.

Workflow:
1) Let user choose reference image
2) Get reference image settings
3) Let user define ramp range + feedback on of off,...
4) Start automated series
5) Stop and turn feedback on + triggers off
"""

#Import tkinter for GUI
import tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import filedialog

#We'll mare use of numpy
import numpy as np
#Import os to help with filename stuff
import os
#Import stuff needed for Matplotlib
import matplotlib as mpl
#import my SMP analysis library
import SPM_Analysis as sa

#To do image analysis
import spiepy
from scipy.ndimage import gaussian_filter

"""Now we define the GUI parts, starting with the main window """
class MainWindow:
    """
    Here we create the main window when opening op the program. It is
    supposed to be modular and easily extendible.
    """
    def __init__(self, master):
        # Set up the GUI
        #self.connectCommand = connectCommand
        self.master = master
        self.master.resizable(False, False)
        # First block is the Code to load a reference image
        self.ReferenceFrame = tkinter.Frame(master, height = 100, width = 300)
        self.Reference = tkinter.Button(self.ReferenceFrame, text='Choose reference \n image and parameters',
            command=self.temp)
        self.Reference.place(relx=.5, rely=.5, anchor="center")
        self.ReferenceFrame.pack(side = "top")
        self.ReferenceFrame.propagate(0)
        print((self.Reference.winfo_width()))


        # Lock-in Control
        self.SeriesFrame  = tkinter.Frame(master, height = 100, width = 300)
        self.Series = tkinter.Button(self.SeriesFrame, text='Define \n series',
            command=self.temp)
        self.Series.place(relx=.5, rely=.5, anchor="center")
        self.Series["state"] = "disabled"
        self.SeriesFrame.pack(side = "top")
        self.SeriesFrame.propagate(0)

    def temp(self):
        print((self.Reference.winfo_width()))

root = tkinter.Tk()
root.add_param = {}

client = MainWindow(root)
root.mainloop()
