# -*- coding: utf-8 -*-
#
#   Copyright © 2014 - 2018 Stephan Zevenhuizen
#   access2theMatrix, (04-03-2018).
#

from __future__ import unicode_literals
from six import iteritems

import os, re
import numpy as np
#Struct converts between C struct and Python value
# unpack(self, buffer, /) Return a tuple containing unpacked values.
from struct import unpack
from time import localtime, strftime


class _Curve_Mode:
    '''
        Looks like types of spectoscopy supported.
        Several interesting types are lacking at the moment.
        Supportes is X(V) and X(Z). Force curve, or arbitrary for instance
        doesn't seem supported
    '''
    SPS_CURVE_V = 'SPS Curve (V)'
    SPS_CURVE_Z = 'SPS Curve (Z)'
    PHASE_AMPLITUDE_CURVE = 'Phase/Amplitude Curve'
    NOT_SUPPORTED = 'Not supported'


class Im(object):
    '''
        Generator of a container for an image with its parameters
    '''
    def __init__(self):
        self.data = np.array([[]])
        self.width = 0
        self.height = 0
        self.y_offset = 0
        self.x_offset = 0
        self.angle = 0
        self.channel_name_and_unit = ['', '']
        self.z_offset = 0
        self.feedback_enabled = False


class Cu(object):
    '''
        Generator of a container for a curve with its parameters
    '''
    def __init__(self):
        self.data = np.array([[]])
        self.referenced_by = {'Data File Name': '', 'Channel': '',
                              'Bricklet Number': 0, 'Run Cycle': 0,
                              'Scan Cycle': 0, 'Trace': [0, ''],
                              'Location (px)': [0, 0], 'Location (m)': [0, 0]}
        self.x_data_name_and_unit = ['', '']
        self.y_data_name_and_unit = ['', '']


class MtrxData(object):
    '''
        The methods to open SPM Image, SPS Curve and Phase/Amplitude Curve
        result files, to select one out of the four possible traces
        (forward/up, backward/up, forward/down and backward/down) for images
        and to select one out of the two possible traces (trace, retrace) for
        curves. Includes method for experiment element parameters overview.
    '''
    ALL_1D_TRACES = ['trace', 'retrace']

    ALL_2D_TRACES = ['forward/up',   'backward/up',
                     'forward/down', 'backward/down']

#Prepare to load a block of data. At this point I do not think that there is a
#difference between curve and image.
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

    #Calculate coordinate syste. One has to check is this works for curves.
    def _rotate_offset(self, centre, offset, angle):
        r_offset_x = offset[0] - centre[0]
        r_offset_y = offset[1] - centre[1]
        a = np.deg2rad(angle)
        x = r_offset_x * np.cos(a) - r_offset_y * np.sin(a) + centre[0]
        y = r_offset_x * np.sin(a) + r_offset_y * np.cos(a) + centre[1]
        offset = [x, y]
        return offset

    #As data comes in some C++ format, it is read the hard way
    def _read_string(self, dp, data_block):
        dl = 4
        dln = unpack('<L', data_block[dp:dp + dl])[0]
        dp += dl
        dl = dln * 2
        return dp + dl, data_block[dp:dp + dl].decode('utf-16')

    #As data comes in some C++ format, it is read the hard way
    def _read_data(self, dp, dp_plus, data_block):
        dl = 4
        dl += dp_plus
        id = data_block[dp + dp_plus:dp + dl].decode()
        dp += dl
        if id == 'LOOB':
            dl = 4
            dpn = dp + dl
            data = bool(unpack('<L', data_block[dp:dpn])[0])
        elif id == 'GNOL':
            dl = 4
            dpn = dp + dl
            data = unpack('<l', data_block[dp:dpn])[0]
        elif id == 'BUOD':
            dl = 8
            dpn = dp + dl
            data = unpack('<d', data_block[dp:dpn])[0]
        elif id == 'GRTS':
            dpn, data = self._read_string(dp, data_block)
        return dpn, data

    #Here be dragons
    def _scan_raw_param(self, dp, data):
        dl = 4
        id = data[dp:dp + dl].decode()
        dp += dl
        dln = unpack('<L', data[dp:dp + dl])[0]
        #print("id = " + str(id))
        dp += dl
        dl = dln
        #print("dln = " + str(dln))
        if (id == 'REFX' or id == 'NACS' or id == 'TCID' or id == 'SCHC' or
            id == 'TSNI' or id == 'SXNC' or id == 'LNEG'):
            dp_plus = 0
            dl += 0
        else:
            dp_plus = 8
            dl += 8
        data_block = data[dp + dp_plus:dp + dl]
        #print("data_block = " + str(data_block))
        if id == 'DPXE':
            dpb = 4
            i = 0
            len_data_block = len(data_block)
            while dpb < len_data_block:
                dpb, s = self._read_string(dpb, data_block)
                #print(s)
                #print(id[::-1])
                self.param[id[::-1] + '::s{0}'.format(i)] = s
                i += 1
        elif id == 'APEE':
            dpb = 8
            n_keys1 = unpack('<L', data_block[4:dpb])[0]
            for i in range(n_keys1):
                dpb, s = self._read_string(dpb, data_block)
                #print(s)
                key1 = id[::-1] + '::{0}'.format(s)
                dlb = 4
                n_keys2 = unpack('<L', data_block[dpb:dpb + dlb])[0]
                #print(n_keys2)
                dpb += dlb
                for j in range(n_keys2):
                    dpb, prop = self._read_string(dpb, data_block)
                    dpb, unit = self._read_string(dpb, data_block)
                    dpb, data = self._read_data(dpb, 4, data_block)
                    key = '{0}.{1}'.format(key1, prop)
                    #print(key, data, unit)
                    self.param[key] = [data, unit]

        # Deze is belangrijk. Hier worden alle veranderingen van experimentele waarden bijgehouden.
        # Zoals offset, scan area, points, setpoint, voltage,...
        elif id == 'DOMP':
            dpb = 4
            dpb, eepa = self._read_string(dpb, data_block)
            dpb, prop = self._read_string(dpb, data_block)
            dpb, unit = self._read_string(dpb, data_block)
            dpb, data = self._read_data(dpb, 4, data_block)

            # print(eepa)
            # print(prop)
            # print(unit)
            # print(data)
            key1 = 'EEPA::{0}'.format(eepa)
            key = '{0}.{1}'.format(key1, prop)
            self.param[key] = [data, unit]

        elif id == 'YSCC':
            dpb = 4
            len_data_block = len(data_block)
            while dpb < len_data_block:
                dpb = self._scan_raw_param(dpb, data_block)
                #print(dpb)
            self.param[id[::-1]] = ''

        elif id == 'TCID':
            dpb = 12
            n_keys = unpack('<L', data_block[8:dpb])[0]
            #print(n_keys)
            for i in range(n_keys):
                dpb += 16
                dpb, key = self._read_string(dpb, data_block)
                dpb, data = self._read_string(dpb, data_block)
                #print(key, data)
            dlb = 4
            n_keys = unpack('<L', data_block[dpb:dpb + dlb])[0]
            #print(n_keys)
            dpb += dlb
            for i in range(n_keys):
                dpb += 4
                key = unpack('<L', data_block[dpb:dpb + dlb])[0]
                dpb += dlb + 8
                dpb, name = self._read_string(dpb, data_block)
                dpb, unit = self._read_string(dpb, data_block)
                #print(name, unit)
                self.param[id[::-1] + '::{0}'.format(key)] = [name, unit]
            n_keys = unpack('<L', data_block[dpb:dpb + dlb])[0]
            #print(n_keys)
            dpb += dlb
            for i in range(n_keys):
                dlb = 8
                s = data_block[dpb:dpb + dlb]
                #print(s)
                if isinstance(s[0], str):
                    channel_id = ''.join(['{:02x}'.format(ord(c))
                                          for c in s[::-1]])
                else:
                    channel_id = ''.join(['{:02x}'.format(c) for c in s[::-1]])
                dpb += dlb + 4
                dlb = 4
                key = unpack('<L', data_block[dpb:dpb + dlb])[0]
                dpb += dlb
                dpb, data = self._read_string(dpb, data_block)
                #print(dpb)
                #print(data)
                self.param[id[::-1] + '::{0}'.format(key)] += [channel_id, data]
                #print(channel_id, data)
                self.channel_id[channel_id] = self.param[id[::-1] + '::{0}'.\
                                                         format(key)][0]
        elif id == 'REFX':
            dpb = 0
            dlb = 4
            len_data_block = len(data_block)
            while dpb < len_data_block:
                dpb += 4
                key1 = unpack('<L', data_block[dpb:dpb + dlb])[0]
                #print(key1)
                dpb += dlb
                dpb, name = self._read_string(dpb, data_block)
                #print("Name is: "+ str(name))
                dpb, unit = self._read_string(dpb, data_block)
                #print("Unit is: "+ str(unit))
                n_keys = unpack('<L', data_block[dpb:dpb + dlb])[0]
                #print(n_keys)
                dpb += dlb
                channel_parameters = {}
                for i in range(n_keys):
                    dpb, key2 = self._read_string(dpb, data_block)
                    dpb, data = self._read_data(dpb, 0, data_block)
                    channel_parameters[key2] = data
                    #rint(key2, data, name, unit, channel_parameters)
                self.param[id[::-1] + '::{0}'.format(key1)] = \
                                    [name, unit, channel_parameters]

        # Hier worden de filenames uit de container gehaald.
        elif id == 'FERB':
            dpb = 4
            dpb, filename = self._read_string(dpb, data_block)
            #print(filename)
            self.param[id[::-1]] = filename




        # Somehow worden hier de STL locaties opgehaald, en ook welke kanalen
        # wel of niet opgeslagen worden.
        elif id == 'KRAM':
            dpb = 0
            dpb, mark = self._read_string(dpb, data_block)
            #print(mark)
            s1 = re.search(r'(^MTRX)\$(.*?)-(.*)', mark)
            if s1:
                s2 = re.search(r'(\d+),(\d+);(.*?),(.*?)(%%.*%%)', s1.group(3))
                if s2 and s1.group(2) == 'STS_LOCATION':
                    v = [int(s2.group(1)), int(s2.group(2)), float(s2.group(3)),
                         float(s2.group(4)), s2.group(5)]
                    if self.raw_data == []:
                        self.sts_locations.append(v)
                else:
                    v = s1.group(3)

                self.param[id[::-1] + '::{0}.{1}'.format(s1.group(1),
                                                         s1.group(2))] = v
        else:
            self.param[id[::-1]] = ''
        #print(dp)
        #print(dl)
        return dp + dl

    #Here be dragons
    def _scan_raw_data(self, dp, data):
        dl = 4
        id = data[dp:dp + dl].decode()
        #print(id)
        dp += dl
        dln = unpack('<L', data[dp:dp + dl])[0]
        dp += dl
        dl = dln
        if (id == 'CSED' or id == 'ATAD'):
            dp_plus = 0
            dl += 0
        else:
            dp_plus = 0
            dl += 8
        data_block = data[dp + dp_plus:dp + dl]
        #print(data_block)
        if id == 'TLKB':
            dpb = 8
            secs = unpack('<Q', data_block[0:dpb])[0]
            #print(secs)
            self.param[id[::-1]] = strftime('%A, %d %B %Y %H:%M:%S',
                                            localtime(secs))
            dpb += 4
            len_data_block = len(data_block)
            while dpb < len_data_block:
                dpb = self._scan_raw_data(dpb, data_block)
        elif id == 'CSED':
            dlb = 4
            dpb = 20
            dpn = dpb + dlb
            self.bricklet_size = unpack('<i', data_block[dpb:dpn])[0]
            dpb = dpn
            dpn = dpb + dlb
            self.data_item_count = unpack('<i', data_block[dpb:dpn])[0]
        elif id == 'ATAD':
            fmt = '<%di' % self.data_item_count
            self.data = np.array(unpack(fmt, data_block))
        return dp + dl

    #Here be dragons
    def _transfer(self, data):
        keys = [k for k in self.param if re.match('DICT::', k)]
        key_nr = str(sorted([int(k[6:]) for k in keys
                             if self.param[k][0] == self.channel_name])[-1])
        self.channel_name_and_unit = self.param['DICT::' + key_nr][:2]
        key = 'XFER::' + key_nr
        name = self.param[key][0]
        p = self.param[key][2]
        if name == 'TFF_Linear1D':
            r = (data - p['Offset']) / p['Factor']
        elif name == 'TFF_MultiLinear1D':
            r = (p['Raw_1'] - p['PreOffset']) * (data - p['Offset']) / \
                (p['NeutralFactor'] * p['PreFactor'])
        else:
            r = data
        return r

    def _im_data(self):
        axis_mirrored = [self.param['EEPA::XYScanner.X_Retrace'][0],
                         self.param['EEPA::XYScanner.Y_Retrace'][0]]
        xm = int(axis_mirrored[0])
        ym = int(axis_mirrored[1])
        xc = self.param['EEPA::XYScanner.Points'][0]
        yc = self.param['EEPA::XYScanner.Lines'][0]
        ylc = yc
        axis_length = [self.param['EEPA::XYScanner.Width'][0],
                       self.param['EEPA::XYScanner.Height'][0]]
        axis_offset = [self.param['EEPA::XYScanner.X_Offset'][0],
                       self.param['EEPA::XYScanner.Y_Offset'][0]]
        axis_clock_count_x = xc * (1 + xm)
        ytc = self.data_item_count // axis_clock_count_x
        if ytc <= yc:
            yc = ytc
            axis_mirrored[1] = False
        ym = int(axis_mirrored[1])
        z = self._transfer(self.data[:axis_clock_count_x * ytc])
        scan = np.empty(((1 + ym) * (1 + xm), yc, xc))
        z = np.reshape(z, (-1, xc))
        if axis_mirrored[0] and axis_mirrored[1]:
            scan[0] = z[:yc * 2:2]
            scan[1] = z[1:yc * 2:2][:, ::-1]
            scan[2, 2 * yc - ytc:] = z[yc * 2::2][::-1]
            scan[3, 2 * yc - ytc:] = z[yc * 2 + 1::2][::-1, ::-1]
        elif axis_mirrored[0] and not axis_mirrored[1]:
            scan[0] = z[:yc * 2:2]
            scan[1] = z[1:yc * 2:2][:, ::-1]
        elif not axis_mirrored[0] and axis_mirrored[1]:
            scan[0] = z[:yc]
            scan[1, 2 * yc - ytc:] = z[yc:][::-1]
        else:
            scan[0] = z
        axis = [[axis_offset[0], axis_length[0]],
                [axis_offset[1], axis_length[1]],
                [axis_mirrored[0], axis_mirrored[1], ylc, ytc],
                ['x', 'm', 'y', 'm']]
        if scan.shape[1] < 2 or scan.shape[2] < 2:
            scan = np.empty((1, 0, 0))
        return scan, axis

    def _cu_data(self):
        if '(V)' in self.channel_name:
            self.curve_mode = _Curve_Mode.SPS_CURVE_V
            retrace = self.param['EEPA::Spectroscopy.Enable_'
                                 'Device_1_Ramp_Reversal'][0]
            x_start, unit = self.param['EEPA::Spectroscopy.Device_1_Start']
            x_end = self.param['EEPA::Spectroscopy.Device_1_End'][0]
            x_points = self.param['EEPA::Spectroscopy.Device_1_Points'][0]
            self.x_points = self.param['EEPA::Spectroscopy.Device_1_Points'][0]
            self.x_data_name_and_unit = ['Spectroscopy Device 1', unit]
        elif '(Z)' in self.channel_name:
            self.curve_mode = _Curve_Mode.SPS_CURVE_Z
            retrace = self.param['EEPA::Spectroscopy.Enable_'
                                 'Device_2_Ramp_Reversal'][0]
            x_start, unit = self.param['EEPA::Spectroscopy.Device_2_Start']
            x_end = self.param['EEPA::Spectroscopy.Device_2_End'][0]
            x_points = self.param['EEPA::Spectroscopy.Device_2_Points'][0]
            self.x_points = self.param['EEPA::Spectroscopy.Device_2_Points'][0]
            self.x_data_name_and_unit = ['Spectroscopy Device 2', unit]
        elif self.channel_name in ['Amplitude(f)', 'Phase(f)']:
            self.curve_mode = _Curve_Mode.PHASE_AMPLITUDE_CURVE
            retrace = False
            x_start, unit = self.param['EEPA::FrequencyPhaseDetector.Start']
            x_end = self.param['EEPA::FrequencyPhaseDetector.End'][0]
            x_points = self.param['EEPA::FrequencyPhaseDetector.Points'][0]
            self.x_points = self.param['EEPA::FrequencyPhaseDetector.Points'][0]
            self.x_data_name_and_unit = ['Frequency/Phase Detector', unit]
        else:
            self.curve_mode = _Curve_Mode.NOT_SUPPORTED
            retrace = False
            x_start, unit = [0, '---']
            x_end = 1
            x_points = self.data_item_count
            self.x_data_name_and_unit = ['---', unit]
        if (self.curve_mode == _Curve_Mode.SPS_CURVE_V or
            self.curve_mode == _Curve_Mode.SPS_CURVE_Z):
            setattr(self, 'ref_by', [None] * 6)
            key = 'MARK::MTRX.STS_LOCATION'
            if key in self.param:
                s1 = re.search(r'(?<=%%)([a-f\d]+?)-(\d+?)-(\d+?)-(\d)',
                               self.param[key][4].lower())
                if s1:
                    channel_id = '{:0>16}'.format(s1.group(1))
                    if channel_id in self.channel_id:
                        self.ref_by = [self.channel_id[channel_id]]
                    else:
                        self.ref_by = [None]
                    self.ref_by.append(int(s1.group(2)))
                    self.ref_by.append(int(s1.group(3)))
                    if self.ref_by[0]:
                        self.ref_by += self._get_ref_by(*self.ref_by)
                    else:
                        self.ref_by += [None, None]
                    self.ref_by.append([int(s1.group(4)),
                                        self.ALL_2D_TRACES[int(s1.group(4))]])
        if self.data_item_count <= x_points and retrace:
            retrace = False
        x = np.linspace(x_start, x_end, x_points)
        y = self._transfer(self.data)
        y = np.reshape(np.resize(y, x_points * (1 + int(retrace))),
                       (-1, x_points))
        if retrace:
            y[1] = y[1, ::-1]
        scan = np.vstack((x, y))
        return scan

    def _get_ref_by(self, channel, bricklet_nr, run_cycle):
        dir_name = os.path.dirname(self.result_data_file)
        base_name = os.path.basename(self.result_data_file)
        gen_base_name = base_name[:base_name.rindex('--')]
        if not dir_name:
            dir_name = '.'
        list_dir = os.listdir(dir_name)
        scan_cycle = None
        data_file_name = None
        first_part = gen_base_name + '--' + str(run_cycle) + '_'
        last_part = '.' + channel + '_mtrx'
        for i in list_dir:
            s1 = re.search(re.escape(first_part) + r'(\d+?)' +
                           re.escape(last_part), i)
            if s1:
                file_name = first_part + s1.group(1) + last_part
                try:
                    with open(os.path.join(dir_name, file_name), 'rb') as f:
                        f.seek(48)
                        bricklet_nr_file = unpack('<L', f.read(4))[0]
                except:
                    bricklet_nr_file = -1
                if bricklet_nr_file == bricklet_nr:
                    scan_cycle = int(s1.group(1))
                    data_file_name = file_name
        return scan_cycle, data_file_name

    def open(self, result_data_file):
        #Initialize all values to 0
        self.curve_mode = None
        if hasattr(self, 'ref_by'):
            delattr(self, 'ref_by')
        self.result_data_file = result_data_file
        self.channel_name_and_unit = ['', '']
        self.x_data_name_and_unit = ['', '']
        self.creation_comment = ''
        self.data_set_name = ''
        self.sample_name = ''
        self.param = {'BREF': ''}
        self.channel_id = {}
        self.bricklet_size = 0
        self.data_item_count = 0
        self.data = np.array([])
        #Use the result file name to guess the parameter file Name
        #You can also get channel name and some details from extension
        try:
            last_part = result_data_file[result_data_file.rindex('--') + 2:]
             #print(last_part)
            index_delimiter = [last_part.index('_'), last_part.index('.'),
                               last_part.rindex('_')]
            #print(index_delimiter)
            self.session = last_part[:index_delimiter[0]]
            self.cycle = last_part[index_delimiter[0] + 1:index_delimiter[1]]
            self.channel_name = last_part[index_delimiter[1] +
                                          1:index_delimiter[2]]
            result_file_chain = result_data_file[:result_data_file.rfind('--')]
            #print(result_file_chain)
            result_file_chain += '_0001.mtrx'
            #print(result_file_chain)
            f = open(result_data_file, 'rb')
            self.raw_data = f.read()
            f.close()
            f = open(result_file_chain, 'rb')
            self.raw_param = f.read()
            f.close()
        except:
            self.session = ''
            self.cycle = ''
            self.channel_name = ''
            self.raw_data = ''
            self.raw_param = ''
        #All Omicron Matrix files start with the same string.
        id_img_ok = self.raw_data[:len(self._file_id)] == self._file_id
        #print(str(self.raw_data[:len(self._file_id)]))
        #print('id img_ok = ' + str(id_img_ok))
        id_par_ok = self.raw_param[:len(self._file_id)] == self._file_id
        #print('id par_ok = ' + str(id_par_ok))
        filename = os.path.basename(result_data_file)
        #print(filename)
        #If both result file and parameter file start with the omicron
        #string, we can start
        if id_img_ok and id_par_ok:
            try:
                dp = 12
                len_raw_param = len(self.raw_param)
                while dp < len_raw_param and self.param['BREF'] != filename:
                    dp = self._scan_raw_param(dp, self.raw_param)
                dp = 12
                dp = self._scan_raw_data(dp, self.raw_data)
                error = False
                #Don't ask me how, but here self.param contains all the parameters one could want
                #print(self.param)
            except:
                error = True
            if error:
                scan = None
                axis = None
                message = 'Error in data file ' + filename + '.'
            else:
                key = 'MARK::MTRX.CREATION_COMMENT'
                if key in self.param:
                    self.creation_comment = self.param[key]
                key = 'MARK::MTRX.DATA_SET_NAME'
                if key in self.param:
                    self.data_set_name = self.param[key]
                key = 'MARK::MTRX.SAMPLE_NAME'
                if key in self.param:
                    self.sample_name = self.param[key]
                if '(' in self.channel_name:
                    try:
                        scan = self._cu_data()
                    except:
                        scan = np.empty((1, 0))
                    axis = None
                else:
                    try:
                        scan, axis = self._im_data()
                    except:
                        scan = np.empty((1, 0, 0))
                        axis = None
                if all(scan.shape):
                    message = 'Successfully opened and processed '\
                              'data file ' + filename + '.'
                elif scan is None:
                    message = 'Error in processing data file ' + filename + \
                              '.'
                else:
                    scan = None
                    axis = None
                    message = 'No data in data file ' + filename + '.'
        else:
            scan = None
            axis = None
            message = 'Error in opening ' + filename + '.'
        self.scan = scan
        self.axis = axis
        if axis:
            i = np.array([True, axis[2][0], axis[2][1],
                          axis[2][0] and axis[2][1]])
            self.traces = list(np.array(self.ALL_2D_TRACES)[i])
        elif scan is not None:
            i = np.array([True, scan.shape[0] == 3])
            self.traces = list(np.array(self.ALL_1D_TRACES)[i])
        else:
            self.traces = []
        traces = dict(enumerate(self.traces))
        return traces, message

    def select_image(self, trace):
        im = Im()
        if trace in self.traces and self.axis:
            key = 'EEPA::XYScanner.Angle'
            if key in self.param:
                im.angle = self.param[key][0]
            else:
                del(im.angle)
                #next lines added by Koen
                #if you want more parameters, add more code
            key = 'EEPA::Regulator.Z_Offset'
            if key in self.param:
                im.z_offset = self.param[key][0]
            key = 'EEPA::Regulator.Feedback_Loop_Enabled'
            if key in self.param:
                im.feedback_enabled = self.param[key][0]
            key = 'EEPA::GapVoltageControl.Voltage'
            if key in self.param:
                im.voltage = self.param[key][0]
            if "AFM" in self.session:
                key = 'EEPA::Regulator.Setpoint_2'
                if key in self.param:
                    im.current = self.param[key][0]
            else:
                key = 'EEPA::Regulator.Setpoint_1'
                if key in self.param:
                    im.current = self.param[key][0]
            key = 'EEPA::XYScanner.Height'
            if key in self.param:
                im.XY_height = self.param[key][0]
            key = 'EEPA::XYScanner.Width'
            if key in self.param:
                im.XY_width = self.param[key][0]
            key = 'EEPA::XYScanner.Points'
            if key in self.param:
                im.XY_points = self.param[key][0]
            key = 'EEPA::XYScanner.Lines'
            if key in self.param:
                im.XY_lines = self.param[key][0]
            key = 'EEPA::XYScanner.X_Offset'
            if key in self.param:
                im.XY_x_offset = self.param[key][0]
            key = 'EEPA::XYScanner.Y_Offset'
            if key in self.param:
                im.XY_y_offset = self.param[key][0]

            im.width = self.axis[0][1]
            data = self.scan[self.traces.index(trace)]
            yc = data.shape[0]
            ylc = self.axis[2][2]
            ytc = self.axis[2][3]
            height = self.axis[1][1]
            x_offset = self.axis[0][0]
            y_offset = self.axis[1][0]
            centre = [x_offset, y_offset]
            if self.ALL_2D_TRACES.index(trace) > 1:
                im.data = np.copy(data[2 * yc - ytc:])
                im.height =  height * (ytc - ylc) / ylc
                offset = [x_offset, y_offset + 0.5 * (height - im.height)]
            else:
                im.data = np.copy(data)
                im.height = height * yc / ylc
                offset = [x_offset, y_offset + 0.5 * (im.height - height)]
            if im.angle:
                offset = self._rotate_offset(centre, offset, im.angle)
            im.x_offset = offset[0]
            im.y_offset = offset[1]
            im.channel_name_and_unit = self.channel_name_and_unit
            message = 'Trace ' + str(trace) + ' selected.'
        else:
            message = 'Error, ' + str(trace) + ' trace not available.'
        return im, message

    def select_curve(self, trace):
        cu = Cu()
        if trace in self.traces and not self.axis:
            key = 'MARK::MTRX.STS_LOCATION'
            if (self.curve_mode == _Curve_Mode.PHASE_AMPLITUDE_CURVE or
                self.curve_mode == _Curve_Mode.NOT_SUPPORTED):
                del(cu.referenced_by)
            elif key in self.param:
                cu.referenced_by['Location (px)'] = self.param[key][0:2]
                cu.referenced_by['Location (m)'] = self.param[key][2:4]
                cu.referenced_by['Channel'] = self.ref_by[0]
                cu.referenced_by['Bricklet Number'] = self.ref_by[1]
                cu.referenced_by['Run Cycle'] = self.ref_by[2]
                cu.referenced_by['Scan Cycle'] = self.ref_by[3]
                cu.referenced_by['Data File Name'] = self.ref_by[4]
                cu.referenced_by['Trace'] = self.ref_by[5]
            else:
                del(cu.referenced_by)
            cu.x_data_name_and_unit = self.x_data_name_and_unit
            cu.y_data_name_and_unit = self.channel_name_and_unit
            x = self.scan[0]
            y = self.scan[self.ALL_1D_TRACES.index(trace) + 1]
            if self.ALL_1D_TRACES.index(trace):
                start = 2 * x.size - self.data_item_count
                cu.data = np.copy([x[start:], y[start:]])
            else:
                if self.data_item_count > x.size:
                    points = x.size
                else:
                    points = self.data_item_count
                cu.data = np.copy([x[:points], y[:points]])
            message = str(trace) + ' selected.'
            message = message[0].upper() + message[1:]
            cu.x_points = self.x_points
        else:
            message = 'Error, ' + str(trace) + ' not available.'
        return cu, message

    #here be dragons
    def get_experiment_element_parameters(self):
        eepas = sorted([[k[6:]] + v for k, v in iteritems(self.param)
                                if re.match('EEPA::', k)])
        message = '{0:<55} {1:>25} {2:<12}\n'.format('Parameter', 'Value',
                                                     'Unit')
        message += '-' * 89 + '\n'

        #print(message)
        for i in eepas:
            message += '{0:<55} {1!s:>25} {2:<12}\n'.format(*i)
            #print(message)
        return eepas, message

class ResultFilechain(object):
    '''
        The methods to open SPM Image, SPS Curve and Phase/Amplitude Curve
        result files, to select one out of the four possible traces
        (forward/up, backward/up, forward/down and backward/down) for images
        and to select one out of the two possible traces (trace, retrace) for
        curves. Includes method for experiment element parameters overview.
    '''
    ALL_1D_TRACES = ['trace', 'retrace']

    ALL_2D_TRACES = ['forward/up',   'backward/up',
                     'forward/down', 'backward/down']

#Prepare to load a block of data. At this point I do not think that there is a
#difference between curve and image.
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



    #As data comes in some C++ format, it is read the hard way
    def _read_string(self, dp, data_block):
        dl = 4
        dln = unpack('<L', data_block[dp:dp + dl])[0]
        dp += dl
        dl = dln * 2
        return dp + dl, data_block[dp:dp + dl].decode('utf-16')

    #As data comes in some C++ format, it is read the hard way
    def _read_data(self, dp, dp_plus, data_block):
        dl = 4
        dl += dp_plus
        id = data_block[dp + dp_plus:dp + dl].decode()
        dp += dl
        if id == 'LOOB':
            dl = 4
            dpn = dp + dl
            data = bool(unpack('<L', data_block[dp:dpn])[0])
        elif id == 'GNOL':
            dl = 4
            dpn = dp + dl
            data = unpack('<l', data_block[dp:dpn])[0]
        elif id == 'BUOD':
            dl = 8
            dpn = dp + dl
            data = unpack('<d', data_block[dp:dpn])[0]
        elif id == 'GRTS':
            dpn, data = self._read_string(dp, data_block)
        return dpn, data

    #Here be dragons
    def _scan_raw_param(self, dp, data):
        dl = 4
        id = data[dp:dp + dl].decode()
        dp += dl
        dln = unpack('<L', data[dp:dp + dl])[0]
        #print(id)
        dp += dl
        dl = dln
        #print(dln)
        if (id == 'REFX' or id == 'NACS' or id == 'TCID' or id == 'SCHC' or
            id == 'TSNI' or id == 'SXNC' or id == 'LNEG'):
            dp_plus = 0
            dl += 0
        else:
            dp_plus = 8
            dl += 8
        data_block = data[dp + dp_plus:dp + dl]
        if id == 'DPXE':
            dpb = 4
            i = 0
            len_data_block = len(data_block)
            while dpb < len_data_block:
                dpb, s = self._read_string(dpb, data_block)
                #still dragons
                #print(s)
                self.param[id[::-1] + '::s{0}'.format(i)] = s
                i += 1
        elif id == 'APEE':
            dpb = 8
            n_keys1 = unpack('<L', data_block[4:dpb])[0]
            for i in range(n_keys1):
                dpb, s = self._read_string(dpb, data_block)
                key1 = id[::-1] + '::{0}'.format(s)
                dlb = 4
                n_keys2 = unpack('<L', data_block[dpb:dpb + dlb])[0]
                dpb += dlb
                for j in range(n_keys2):
                    dpb, prop = self._read_string(dpb, data_block)
                    dpb, unit = self._read_string(dpb, data_block)
                    dpb, data = self._read_data(dpb, 4, data_block)
                    key = '{0}.{1}'.format(key1, prop)
                    #more dragons
                    #print(prop, data, unit)
                    self.param[key] = [data, unit]
        elif id == 'DOMP':
            dpb = 4
            dpb, eepa = self._read_string(dpb, data_block)
            dpb, prop = self._read_string(dpb, data_block)
            dpb, unit = self._read_string(dpb, data_block)
            dpb, data = self._read_data(dpb, 4, data_block)
            key1 = 'EEPA::{0}'.format(eepa)
            key = '{0}.{1}'.format(key1, prop)
            #why still dragons
            #print(prop, data, unit)
            self.param[key] = [data, unit]
        elif id == 'YSCC':
            dpb = 4
            len_data_block = len(data_block)
            while dpb < len_data_block:
                dpb = self._scan_raw_param(dpb, data_block)
            self.param[id[::-1]] = ''
        elif id == 'TCID':
            dpb = 12
            n_keys = unpack('<L', data_block[8:dpb])[0]
            for i in range(n_keys):
                dpb += 16
                dpb, key = self._read_string(dpb, data_block)
                dpb, data = self._read_string(dpb, data_block)
            dlb = 4
            n_keys = unpack('<L', data_block[dpb:dpb + dlb])[0]
            dpb += dlb
            for i in range(n_keys):
                dpb += 4
                key = unpack('<L', data_block[dpb:dpb + dlb])[0]
                dpb += dlb + 8
                dpb, name = self._read_string(dpb, data_block)
                dpb, unit = self._read_string(dpb, data_block)

                self.param[id[::-1] + '::{0}'.format(key)] = [name, unit]
            n_keys = unpack('<L', data_block[dpb:dpb + dlb])[0]
            dpb += dlb
            for i in range(n_keys):
                dlb = 8
                s = data_block[dpb:dpb + dlb]
                if isinstance(s[0], str):
                    channel_id = ''.join(['{:02x}'.format(ord(c))
                                          for c in s[::-1]])
                else:
                    channel_id = ''.join(['{:02x}'.format(c) for c in s[::-1]])
                dpb += dlb + 4
                dlb = 4
                key = unpack('<L', data_block[dpb:dpb + dlb])[0]
                dpb += dlb
                dpb, data = self._read_string(dpb, data_block)
                self.param[id[::-1] + '::{0}'.format(key)] += [channel_id, data]
                self.channel_id[channel_id] = self.param[id[::-1] + '::{0}'.\
                                                         format(key)][0]
        elif id == 'REFX':
            dpb = 0
            dlb = 4
            len_data_block = len(data_block)
            while dpb < len_data_block:
                dpb += 4
                key1 = unpack('<L', data_block[dpb:dpb + dlb])[0]
                dpb += dlb
                dpb, name = self._read_string(dpb, data_block)
                dpb, unit = self._read_string(dpb, data_block)
                n_keys = unpack('<L', data_block[dpb:dpb + dlb])[0]
                dpb += dlb
                channel_parameters = {}
                for i in range(n_keys):
                    dpb, key2 = self._read_string(dpb, data_block)
                    dpb, data = self._read_data(dpb, 0, data_block)
                    channel_parameters[key2] = data
                self.param[id[::-1] + '::{0}'.format(key1)] = \
                                    [name, unit, channel_parameters]
        elif id == 'FERB':
            dpb = 4
            dpb, filename = self._read_string(dpb, data_block)
            self.filechain.append(filename)
            self.param[id[::-1]] = filename
        elif id == 'KRAM':
            dpb = 0
            dpb, mark = self._read_string(dpb, data_block)
            s1 = re.search(r'(^MTRX)\$(.*?)-(.*)', mark)
            if s1:
                s2 = re.search(r'(\d+),(\d+);(.*?),(.*?)(%%.*%%)', s1.group(3))
                if s2 and s1.group(2) == 'STS_LOCATION':
                    v = [int(s2.group(1)), int(s2.group(2)), float(s2.group(3)),
                         float(s2.group(4)), s2.group(5)]
                else:
                    v = s1.group(3)
                self.param[id[::-1] + '::{0}.{1}'.format(s1.group(1),
                                                         s1.group(2))] = v
        else:
            self.param[id[::-1]] = ''
        #print(dp)
        #print(dl)
        return dp + dl

    #Here be dragons

    #Here be dragons
    def _transfer(self, data):
        keys = [k for k in self.param if re.match('DICT::', k)]
        key_nr = str(sorted([int(k[6:]) for k in keys
                             if self.param[k][0] == self.channel_name])[-1])
        self.channel_name_and_unit = self.param['DICT::' + key_nr][:2]
        key = 'XFER::' + key_nr
        name = self.param[key][0]
        #print(name)
        p = self.param[key][2]
        #print(p)
        if name == 'TFF_Linear1D':
            r = (data - p['Offset']) / p['Factor']
        elif name == 'TFF_MultiLinear1D':
            r = (p['Raw_1'] - p['PreOffset']) * (data - p['Offset']) / \
                (p['NeutralFactor'] * p['PreFactor'])
        else:
            r = data
        return r



    def _get_ref_by(self, channel, bricklet_nr, run_cycle):
        dir_name = os.path.dirname(self.result_data_file)
        base_name = os.path.basename(self.result_data_file)
        gen_base_name = base_name[:base_name.rindex('--')]
        if not dir_name:
            dir_name = '.'
        list_dir = os.listdir(dir_name)
        scan_cycle = None
        data_file_name = None
        first_part = gen_base_name + '--' + str(run_cycle) + '_'
        last_part = '.' + channel + '_mtrx'
        for i in list_dir:
            s1 = re.search(re.escape(first_part) + r'(\d+?)' +
                           re.escape(last_part), i)
            if s1:
                file_name = first_part + s1.group(1) + last_part
                try:
                    with open(os.path.join(dir_name, file_name), 'rb') as f:
                        f.seek(48)
                        bricklet_nr_file = unpack('<L', f.read(4))[0]
                except:
                    bricklet_nr_file = -1
                if bricklet_nr_file == bricklet_nr:
                    scan_cycle = int(s1.group(1))
                    data_file_name = file_name
        return scan_cycle, data_file_name

    def open(self, result_data_file):
        #Initialize all values to 0
        self.curve_mode = None
        if hasattr(self, 'ref_by'):
            delattr(self, 'ref_by')
        self.result_data_file = result_data_file
        self.channel_name_and_unit = ['', '']
        self.x_data_name_and_unit = ['', '']
        self.creation_comment = ''
        self.data_set_name = ''
        self.sample_name = ''
        self.param = {'BREF': ''}
        self.channel_id = {}
        self.bricklet_size = 0
        self.data_item_count = 0
        self.data = np.array([])
        self.filechain = []
        #Use the result file name to guess the parameter file Name
        #You can also get channel name and some details from extension
        try:

            f = open(result_data_file, 'rb')
            self.raw_param = f.read()
            f.close()
        except:
            self.session = ''
            self.cycle = ''
            self.channel_name = ''
            self.raw_data = ''
            self.raw_param = ''
        #All Omicron Matrix files start with the same string.

        #print(str(self.raw_data[:len(self._file_id)]))
        #print('id img_ok = ' + str(id_img_ok))
        id_par_ok = self.raw_param[:len(self._file_id)] == self._file_id
        #print('id par_ok = ' + str(id_par_ok))
        filename = os.path.basename(result_data_file)
        #print(filename)
        #If both result file and parameter file start with the omicron
        #string, we can start
        if id_par_ok:
            try:
                dp = 12
                len_raw_param = len(self.raw_param)
                while dp < len_raw_param:
                    dp = self._scan_raw_param(dp, self.raw_param)
                message = "All ok."
            except:

                message = 'Error in data file ' + filename + '.'


        else:
            scan = None
            axis = None
            message = 'Error in opening ' + filename + '.'

        return self.filechain, message



    def get_experiment_element_parameters(self):
        eepas = sorted([[k[6:]] + v for k, v in iteritems(self.param)
                        if re.match('EEPA::', k)])
        message = '{0:<55} {1:>25} {2:<12}\n'.format('Parameter', 'Value',
                                                     'Unit')
        message += '-' * 89 + '\n'
        for i in eepas:
            message += '{0:<55} {1!s:>25} {2:<12}\n'.format(*i)
        return eepas, message
