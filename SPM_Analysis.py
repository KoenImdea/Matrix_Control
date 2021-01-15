#access2thematrix is to load directly omicron matrix data
import access2thematrix_test as access2thematrix
import spiepy, spiepy.demo
import numpy as np
from scipy.ndimage import gaussian_filter
import os

"""
///To use the object im with the SPIEPy library,
im must change from access2theMatrix Image Structure object to
SPIEPy Image Structure object.
"""

def open_image(file_name, trace_nr = 0):
    """
    Open matrix image files using access2theMatrix
    parameters: file_name, trace_nr=0
    trace_nr 0 is forwards, 1 is backwards
    If up/down is enebled, they would be 3 and 4
    """
    mtrx_data = access2thematrix.MtrxData()

    traces, message = mtrx_data.open(file_name)
    #print(message)
    im, message = mtrx_data.select_image(traces[trace_nr])
    #print(message)
    return im

def open_curve(file_name, trace_nr = 0):
    """
    Open matrix curves files using access2theMatrix
    parameters: file_name, trace_nr=0
    trace_nr 0 is forwards,
    """
    mtrx_data = access2thematrix.MtrxData()

    traces, message = mtrx_data.open(file_name)
    #print(message)
    cu, message = mtrx_data.select_curve(traces[trace_nr])
    #print(message)
    return cu

def line_filtered(image):
    """
    Filter an image linewise by substracting the mean per line for x.
    """
    line_filtered = []
    for i in range(0, image.shape[0]):
        new_x_line = image[i,:]-np.mean(image[i,:])
        line_filtered.append(new_x_line)
    line_filtered = np.asarray(line_filtered)
    return line_filtered

def poly_line_filtered(image, poly_order = 2):
    """
    Filter an image linewise by substracting a fitted polynomal per line.
    Parameters: image (2D np array), poly_order (integer)
    """
    poly_line_filtered = []
    x = np.linspace(0, 1, num = image.shape[1])
    for i in range(0, image.shape[0]):
        param = np.polyfit(x, image[i,:], poly_order)
        fit = np.zeros(x.size)
        for p in range(0, param.size):
            fit = fit + param[p]*x**(param.size-p-1)
        new_x_line = image[i,:]-fit
        poly_line_filtered.append(new_x_line)
    poly_line_filtered = np.asarray(poly_line_filtered)
    return poly_line_filtered

def flatten_by_iterate_mask(image):
    flattened, mask, n = spiepy.flatten_by_iterate_mask(image, mask_method='mean', fit_type='poly2', max_change=5, max_iterations=100, mask_options=[1, 'a', 5], master_mask=None)
    return flattened

def flatten_by_peaks(image):
    flattened, im_plane = spiepy.flatten_by_peaks(image, mask=None, deg=2, sigma=1)
    return flattened

def flatten_xy(image):
    flattened, im_plane = spiepy.flatten_xy(image, mask=None)
    return flattened

def flatten_poly_xy(image, order=2):
    flattened, im_plane = spiepy.flatten_poly_xy(image, mask=None, deg=order)
    return flattened

def find_peaks(image):
    """
    Find all the peaks in an image, using spiepy
    """
    p = spiepy.locate_troughs_and_peaks(image)
    vectors_hills = np.asarray(p[1])
    return vectors_hills

def find_holes(image):
    """
    Find all the holes in an image, using spiepy
    """
    p = spiepy.locate_troughs_and_peaks(image)
    vectors_holes = np.asarray(p[0])
    return vectors_holes

def calculate_distances():
    """
    Calculate the distances between an array of holes or peaks
    """
    i = 0
    distances = []
    for i in range(0, vectors_hills[0].size):
        for n in range(0, vectors_hills[0].size):
            if i == n:
                distances = distances
            else:
                d = ((vectors_hills[0][i]-vectors_hills[0][n])**2 + (vectors_hills[1][i]-vectors_hills[1][n])**2)**(1/2)
                d = d * size_calib
                distances.append(d)
    distances_np = np.asarray(distances)
    return distances

def load_filechain(file):
    """
    Load a complete matrix filechain in order using access2theMatrix
    parameters: file
    """
    filechain = []
    path = os.path.dirname(file) + "\\"
    mtrx_data = access2thematrix.MtrxData()
    f = open(file, 'rb')
    mtrx_data.raw_param = f.read()
    f.close()
    mtrx_data.raw_data = []
    mtrx_data.sts_locations = []
    mtrx_data.sts_names = []
    mtrx_data.sts_dict = {}

    dp = 12
    len_raw_param = len(mtrx_data.raw_param)
    while dp < len_raw_param:
        dp = mtrx_data._scan_raw_param(dp, mtrx_data.raw_param)
        if (mtrx_data.param['BREF'] not in filechain) and not(mtrx_data.param['BREF'] == ""):
            last_part = mtrx_data.param['BREF'][mtrx_data.param['BREF'].rindex('--') + 2:]
            if "(" in last_part:
                if (mtrx_data.param['BREF'] not in mtrx_data.sts_names):
                    mtrx_data.sts_names.append(mtrx_data.param['BREF'])
            elif not(mtrx_data.sts_names==[]):
                mtrx_data.sts_dict[path + mtrx_data.param['BREF']] = [mtrx_data.sts_names, mtrx_data.sts_locations]
                filechain.append(mtrx_data.param['BREF'])
                mtrx_data.sts_names = []
                mtrx_data.sts_locations = []
            else:
                filechain.append(mtrx_data.param['BREF'])
                mtrx_data.sts_locations = []

    for i in range(0, len(filechain)):
        filechain[i] = path + filechain[i]
    for value in mtrx_data.sts_dict.values():
        for i in range(0, len(value[0])):
            value[0][i] = path + value[0][i]
    return filechain, mtrx_data.sts_dict

class IMAGE(object):
    def __init__(self):
        self._file_id = b'ONTMATRX0101'
        self.curve_mode = None
        self.result_data_file = ''
        self.creation_comment = ''
        self.data_set_name = ''
        self.sample_name = ''
        self.session = ''
        self.cycle = ''
        self.channel_name = ''
        self.channel_name_and_unit = ['', '']
        self.x_data_name_and_unit = ['', '']
        self.raw_data = ''
        self.raw_param = ''
        self.param = {'BREF': ''}
        self.channel_id = {}
        self.bricklet_size = 0
        self.data_item_count = 0
        self.data = np.array([])
        self.scan = None
        self.axis = None
        self.traces = []
