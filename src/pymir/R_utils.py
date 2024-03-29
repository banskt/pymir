import os
import numpy as np
import pandas as pd

import rpy2.robjects as robj
import rpy2.robjects.vectors as rvec
from rpy2.robjects.packages import importr
from rpy2.robjects import numpy2ri
numpy2ri.activate()

def array_reduce(x):
    ndim = x.ndim
    if ndim == 1:
        res = x[0] if x.shape[0] == 1 else x
    elif ndim == 2:
        res = x.reshape(-1) if x.shape[1] == 1 else x
    return res

def list_reduce(x):
    ndim = len(x)
    if ndim == 1:
        return x[0]
    else:
        return x


def robj2dict_recursive(obj):
    res = dict()
    for key in obj.names:
        #print (key)
        elem = obj.rx2(key)
        if isinstance(elem, (rvec.FloatVector, rvec.IntVector)):
            res[key] = array_reduce(np.array(elem))
        elif isinstance(elem, rvec.StrVector):
            res[key] = list_reduce(list(elem))
        elif isinstance(elem, np.ndarray):
            res[key] = array_reduce(elem)
        elif isinstance(elem, rvec.ListVector):
            res[key] = robj2dict_recursive(elem)
        elif isinstance(elem, rvec.BoolVector):
            res[key] = array_reduce(np.array(elem, dtype = bool))
        elif all(np.array(robj.r['is.null'](elem))) == True:
            res[key] = None
        #elif elem == robj.NULL:
        #    res[key] = None
    return res


def robj2dict(obj):
    return robj2dict_recursive(obj)


def flatten_list(lst):
    return sum(([x] if not isinstance(x, (list, tuple)) else flatten_list(x)
                for x in lst), [])

def load_rds(filename, types=None):
    import rpy2.robjects as RO
    import rpy2.robjects.vectors as RV
    import rpy2.rinterface as RI
    from rpy2.robjects import numpy2ri
    numpy2ri.activate()
    from rpy2.robjects import pandas2ri
    pandas2ri.activate()

    def load(data, types, rpy2_version=3):
        if types is not None and not isinstance(data, types):
            return np.array([])
        # FIXME: I'm not sure if I should keep two versions here
        # rpy2_version 2.9.X is more tedious but it handles BoolVector better
        # rpy2 version 3.0.1 converts bool to integer directly without dealing with
        # NA properly. It gives something like (0,1,-234235).
        # Possibly the best thing to do is to open an issue for it to the developers.
        if rpy2_version == 2:
            # below works for rpy2 version 2.9.X
            if isinstance(data, RI.RNULLType):
                res = None
            elif isinstance(data, RV.BoolVector):
                data = RO.r['as.integer'](data)
                res = np.array(data, dtype=int)
                # Handle c(NA, NA) situation
                if np.sum(np.logical_and(res != 0, res != 1)):
                    res = res.astype(float)
                    res[res < 0] = np.nan
                    res[res > 1] = np.nan
            elif isinstance(data, RV.FactorVector):
                data = RO.r['as.character'](data)
                res = np.array(data, dtype=str)
            elif isinstance(data, RV.IntVector):
                res = np.array(data, dtype=int)
            elif isinstance(data, RV.FloatVector):
                res = np.array(data, dtype=float)
            elif isinstance(data, RV.StrVector):
                res = np.array(data, dtype=str)
            elif isinstance(data, RV.DataFrame):
                res = pd.DataFrame(data)
            elif isinstance(data, RV.Matrix):
                res = np.matrix(data)
            elif isinstance(data, RV.Array):
                res = np.array(data)
            else:
                # I do not know what to do for this
                # But I do not want to throw an error either
                res = str(data)
        else:
            if isinstance(data, RI.NULLType):
                res = None
            else:
                res = data
        if isinstance(res, np.ndarray) and res.shape == (1, ):
            res = res[0]
        return res

    def load_dict(res, data, types):
        '''load data to res'''
        names = data.names if not isinstance(data.names, RI.NULLType) else [
            i + 1 for i in range(len(data))
        ]
        for name, value in zip(names, list(data)):
            if isinstance(value, RV.ListVector):
                res[name] = {}
                res[name] = load_dict(res[name], value, types)
            else:
                res[name] = load(value, types)
        return res

    #
    if not os.path.isfile(filename):
        raise IOError('Cannot find file ``{}``!'.format(filename))
    rds = RO.r['readRDS'](filename)
    if isinstance(rds, RV.ListVector):
        res = load_dict({}, rds, types)
    else:
        res = load(rds, types)
    return res


def save_rds(data, filename):
    import collections, re
    import rpy2.robjects as RO
    import rpy2.rinterface as RI
    from rpy2.robjects import numpy2ri
    numpy2ri.activate()
    from rpy2.robjects import pandas2ri
    pandas2ri.activate()
    # Supported data types:
    # int, float, str, tuple, list, numpy array
    # numpy matrix and pandas dataframe
    int_type = (int, np.int8, np.int16, np.int32, np.int64)
    float_type = (float, np.float)

    def assign(name, value):
        name = re.sub(r'[^\w' + '_.' + ']', '_', name)
        if isinstance(value, (tuple, list)):
            if all(isinstance(item, int_type) for item in value):
                value = np.asarray(value, dtype=int)
            elif all(isinstance(item, float_type) for item in value):
                value = np.asarray(value, dtype=float)
            else:
                value = np.asarray(value)
        if isinstance(value, np.matrix):
            value = np.asarray(value)
        if isinstance(
                value,
                tuple(flatten_list((str, float_type, int_type, np.ndarray)))):
            if isinstance(value, np.ndarray) and value.dtype.kind == "u":
                value = value.astype(int)
            RO.r.assign(name, value)
        elif isinstance(value, pd.DataFrame):
            # FIXME: does not always work well for pd.DataFrame
            RO.r.assign(name, value)
        elif value is None:
            RO.r.assign(name, RI.NULL)
        else:
            raise ValueError(
                "Saving ``{}`` to RDS file is not supported!".format(
                    str(type(value))))

    #
    def assign_dict(name, value):
        RO.r('%s <- list()' % name)
        for k, v in value.items():
            k = re.sub(r'[^\w' + '_.' + ']', '_', str(k))
            if k.isdigit():
                k = str(k)
            if isinstance(v, collections.Mapping):
                assign_dict('%s$%s' % (name, k), v)
            else:
                assign('item', v)
                RO.r('%s$%s <- item' % (name, k))

    #
    if isinstance(data, collections.Mapping):
        assign_dict('res', data)
    else:
        assign('res', data)
    RO.r("saveRDS(res, '%s')" % filename)
