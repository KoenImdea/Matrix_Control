# -*- coding: utf-8 -*-
#
#   Copyright © 2020 Stephan Zevenhuizen
#   custom_MATE_for_Dummies, (04-04-2020).
#

import mate4dummies.objects as mo
import ctypes


def add_foreign_parameter(*args):
    flat_value = mo.mate.flat_values(0, 0, 1).values[0]
    p_args = ctypes.pointer(mo.mate.flat_values(255, 0, 4))
    for i, arg in enumerate(args[:3]):
        a = arg.encode()
        p_args[0].values[i].type = mo.mate.ValueType.vt_STRING
        p_args[0].values[i].string[0][0].length = len(a)
        p_args[0].values[i].string[0][0].text = a
    if args[1] == 'boolean':
        p_args[0].values[3].type = mo.mate.ValueType.vt_BOOLEAN
        p_args[0].values[3].boolean = args[3]
    elif args[1] in ['long', 'quad']:
        p_args[0].values[3].type = mo.mate.ValueType.vt_INTEGER
        p_args[0].values[3].integer = args[3]
    elif args[1] == 'double':
        p_args[0].values[3].type = mo.mate.ValueType.vt_DOUBLE
        p_args[0].values[3].real = args[3]
    elif args[1] == 'string':
        a = args[3].encode()
        p_args[0].values[3].type = mo.mate.ValueType.vt_STRING
        p_args[0].values[3].string[0][0].length = len(a)
        p_args[0].values[3].string[0][0].text = a
    obj = mo.mate.scope + '.addForeignParameter'
    func_params = [flat_value, 'function', obj, p_args]
    _, mo.mate.rc = mo.mate.remote_access(func_params, 1)
    if mo.mate.rc == mo.mate.rcs['RMT_REJECTED']:
        print('Foreign parameter already exists or wrong data type of the new'
              ' parameter.')

def remove_foreign_parameter(name):
    flat_value = mo.mate.flat_values(0, 0, 1).values[0]
    p_args = ctypes.pointer(mo.mate.flat_values(255, 0, 1))
    a = name.encode()
    p_args[0].values[0].type = mo.mate.ValueType.vt_STRING
    p_args[0].values[0].string[0][0].length = len(a)
    p_args[0].values[0].string[0][0].text = a
    obj = mo.mate.scope + '.removeForeignParameter'
    func_params = [flat_value, 'function', obj, p_args]
    _, mo.mate.rc = mo.mate.remote_access(func_params, 1)

def get_foreign_parameter(name, data_type):
    obj = mo.mate.scope + '.' + name
    if data_type == 'boolean':
        func_params = [False, 'getBoolean', obj]
    elif data_type in ['long', 'quad']:
        func_params = [0, 'getInteger', obj]
    elif data_type == 'double':
        func_params = [0.0, 'getDouble', obj]
    elif data_type == 'string':
        func_params = ['', 'getString', obj]
    else:
        func_params = []
    if func_params:
        out, mo.mate.rc = mo.mate.remote_access(func_params, 1)
    else:
        out = None
    return out

def set_foreign_parameter(name, data_type, value):
    obj = mo.mate.scope + '.' + name
    if data_type == 'boolean':
        func_params = [None, 'setBoolean', obj, value]
    elif data_type in ['long', 'quad']:
        func_params = [None, 'setInteger', obj, value]
    elif data_type == 'double':
        func_params = [None, 'setDouble', obj, value]
    elif data_type == 'string':
        func_params = [None, 'setString', obj, value]
    else:
        func_params = []
    if func_params:
        _, mo.mate.rc = mo.mate.remote_access(func_params, 1)

mo.mate.connect()
if mo.mate.online:
    args_x = [['dummy_0', 'boolean', '', True, False],
              ['dummy_1', 'long', 'count', 2 ** 31 - 1, -(2 ** 31)],
    ### not build in yet in MATE_for_Dummies
    ###       ['dummy_2', 'quad', 'count', 2 ** 63 - 1, -(2 ** 63)],
              ['dummy_3', 'double', 'meter', 1e-9, 2e-9],
              ['dummy_4', 'string', '', 'Hello, World!', 'Bye, bye.']]
    for args in args_x:
        add_foreign_parameter(*args[:4])
        print(get_foreign_parameter(*args[:2]))
        set_foreign_parameter(*args[:2], args[4])
        print(get_foreign_parameter(*args[:2]))
    remove_foreign_parameter('dummy_4')
    print(get_foreign_parameter(*args[:2]))
    #mo.mate.disconnect()
