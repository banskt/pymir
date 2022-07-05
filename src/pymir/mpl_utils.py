import numpy as np
import math
import bisect

def lims_xy(ax):
    lims = [
        np.min([ax.get_xlim(), ax.get_ylim()]),  # min of both axes
        np.max([ax.get_xlim(), ax.get_ylim()]),  # max of both axes
    ]
    return lims


def plot_diag(ax):
    lims = lims_xy(ax)
    ax.plot(lims, lims, ls='dotted', color='gray')


def x_linspace(ax, n=500):
    xlim = ax.get_xlim()
    return np.linspace(xlim[0], xlim[1], n)


def decorate_axes(ax, hide= ["top", "right"], ticklimits = False, pads = [20, 10]):
    # A helper function to show border only within visible tick limits
    def bound_limits(ax, side, border, pads):
        if side in ["bottom", "top"]:
            x0, x1 = ax.get_xlim()
            xticks = [t for t in ax.get_xticks() if t >= x0 and t <= x1]
            border.set_bounds(low = xticks[0], high = xticks[-1])
            border.set_position(('outward', pads[0]))
        if side in ["left", "right"]:
            y0, y1 = ax.get_ylim()
            yticks = [t for t in ax.get_yticks() if t >= y0 and t <= y1]
            border.set_bounds(low = yticks[0], high = yticks[-1])
            border.set_position(('outward', pads[1]))
        return
    # The main function for decorating the axes
    if "all" in hide: hide = ["top", "right", "bottom", "left"]
    for side, border in ax.spines.items():
        if side in hide:
            border.set_visible(False)
        else:
            if ticklimits: bound_limits(ax, side, border, pads)
    return


def float_range(xmin, xmax, sep):
    res = list(np.arange(xmin, xmax, sep))
    # sometimes the last float is ignored due to floating point error
    lastfloat = res[-1] + sep
    if abs(lastfloat - xmax) < 1e-8: res.append(lastfloat)
    return res


def scale_list(x, scale = 'linear'):
    if scale == 'linear':
        xscale = x.copy()
    elif scale == 'log10':
        xscale = [np.log10(y) for y in x]
    elif scale == 'log2':
        xscale = [np.log2(y) for y in x]
    return xscale


def descale_list(x, scale = 'linear'):
    if scale == 'linear':
        xscale = x.copy()
    elif scale == 'log10':
        xscale = [10**y for y in x]
    elif scale == 'log2':
        xscale = [2**y for y in x]
    return xscale


def scale_array(x, scale):
    if scale == 'linear':
        xscale = x.copy()
    elif scale == 'log10':
        xscale = np.log10(x)
    elif scale == 'log2':
        xscale = np.log2(x)
    return xscale



def get_rational_intervals(x, h, kmin, kmax):
    '''
    x: range on the real number axis
    h: proposed intervals
       (integral power of 10, e.g. 100, 10, 0.001, etc)
    kmin: minimum number of intervals
    kmax: maximum number of intervals
    ***
    Strategy:
        h / 2^m should be a rational number that can be
        marked conveniently on the axis.
        Find integer m such that:
            int(x * 2^m / h) > kmin
        If m < 0, then h is too small.
        Find integer m such that:
            int(x / (h * m)) < kmax

    Warning:
        Greedy algorithm enforces kmin / kmax.
        Once new_k is chosen, it does not re-check
        if new_k is <kmax and/or >kmin.
    '''
    hopt = h
    m = math.ceil(np.log2(h * kmin) - np.log2(x))
    if m < 0:
        m = math.ceil(x / (h * kmax))
        hopt = h * m
    else:
        hopt = h / (2**m)
    return hopt


def get_tickmarkers(xmin, xmax, kmin, kmax, spacing = 'linear'):
    assert kmin < kmax, "kmin must be at least one less than kmax"
    '''
    '''
    _xmin, _xmax = scale_list([xmin, xmax], scale = spacing)
    _xrange = _xmax - _xmin
    
    '''
    1. Get position of the first significant digit in the range of x
    2. Use an integral power of 10 for first guess of intervals (h)
    3. Find optimum intervals 
    '''
    spos = math.ceil(np.log10(_xrange)) - 1
    h = 10 ** spos
    if spacing == 'log10':
        hopt = h
    else:
        hopt = get_rational_intervals(_xrange, h, kmin, kmax)
    '''
    Find sanitized minimum value
    '''
    tmin  = int(_xmin / hopt) * hopt
    while tmin < _xmin: tmin += min(h, hopt)
    ticks = float_range(tmin, _xmax, hopt)
    ticks = [round(x, max(8, abs(spos))) for x in ticks]
    ticks_scaled = descale_list(ticks, scale = spacing)
    return ticks_scaled



'''
A helper function to obtain proper tick positions given 
x0 (minimum on the axis) and x1 (maximum on the axis).
kmin = minimum number of ticks
kmax = maximum number of ticks
scale = scale of the axis
spacing = scale of the labels 
          (e.g. spacing = 'log10' would be 10, 100, 1000, etc
                spacing = 'log2' would be 2, 4, 8, etc
                spacing = 'linear' would be 1, 2, 3, etc)
'''
def get_ticks(x0, x1, kmin, kmax, scale = 'linear', spacing = 'linear'):
    # Tick marks should be descaled, while positions should be scaled.
    xmin, xmax = descale_list([x0, x1], scale = scale)
    tmarks     = get_tickmarkers(xmin, xmax, kmin, kmax, spacing = spacing)
    tpos       = scale_list(tmarks, scale = scale)
    return tpos, tmarks


'''
Insert additional tick positions and tick markers in an already sorted
list of positions and markers
'''
def force_insert_ticks(tpos, tmarks, tmarks_insert, scale = 'linear'):
    tpos_insert = scale_list(tmarks_insert, scale = scale)
    tpos_new = tpos.copy()
    tmarks_new = tmarks.copy()
    for pos, mark in zip(tpos_insert, tmarks_insert):
        if mark not in tmarks_new:
            idx = bisect.bisect_left(tpos_new, pos)
            tpos_new.insert(idx, pos)
            tmarks_new.insert(idx, mark)
    return tpos_new, tmarks_new


def set_yticks(ax, kmin = 2, kmax = 6, scale = 'linear', spacing = 'linear', tickmarks = None, 
               rotation = 0, forceticks = None, fmt = '{}'):
    if tickmarks is None:
        y0, y1 = ax.get_ylim()
        tpos, tmarks = get_ticks(y0, y1, kmin, kmax, scale = scale, spacing = spacing)
        if forceticks is not None:
            tpos, tmarks = force_insert_ticks(tpos, tmarks, forceticks, scale = scale)
    else:
        tpos = scale_list(tickmarks, scale = scale)
        tmarks = tickmarks.copy()
    ax.set_yticks(tpos)
    ax.set_yticklabels([fmt.format(x) for x in tmarks], rotation = rotation)
    return


def set_xticks(ax, kmin = 2, kmax = 6, scale = 'linear', spacing = 'linear', tickmarks = None, 
               rotation = 0, forceticks = None, fmt = '{}'):
    if tickmarks is None:
        x0, x1 = ax.get_xlim()
        tpos, tmarks = get_ticks(x0, x1, kmin, kmax, scale = scale, spacing = spacing)
        if forceticks is not None:
            tpos, tmarks = force_insert_ticks(tpos, tmarks, forceticks, scale = scale)
    else:
        tpos = scale_list(tickmarks, scale = scale)
        tmarks = tickmarks.copy()
    ax.set_xticks(tpos)
    ax.set_xticklabels([fmt.format(x) for x in tmarks], rotation = rotation)
    return


def set_soft_ylim(ax, ymin, ymax, scale = 'linear'):
    y0, y1 = ax.get_ylim()
    y2, y3 = scale_list([ymin, ymax], scale)
    ax.set_ylim([min(y0, y2), max(y1, y3)])
    return


def set_soft_xlim(ax, xmin, xmax, scale = 'linear'):
    x0, x1 = ax.get_xlim()
    x2, x3 = scale_list([xmin, xmax], scale)
    ax.set_xlim([min(x0, x2), max(x1, x3)])
    return


def set_ymax(ax, ymax, scale = 'linear'):
    y0, y1 = ax.get_ylim()
    y2 = scale_list([ymax], scale)[0]
    ax.set_ylim([y0, y2])
    return


def set_xmax(ax, xmax, scale = 'linear'):
    x0, x1 = ax.get_xlim()
    x2 = scale_list([xmax], scale)[0]
    ax.set_xlim([x0, x2])
    return


def set_ymin(ax, ymin, scale = 'linear'):
    y0, y1 = ax.get_ylim()
    y2 = scale_list([ymin], scale)[0]
    ax.set_ylim([y2, y1])
    return


def set_xmin(ax, xmin, scale = 'linear'):
    x0, x1 = ax.get_xlim()
    x2 = scale_list([xmin], scale)[0]
    ax.set_xlim([x2, x1])
    return
