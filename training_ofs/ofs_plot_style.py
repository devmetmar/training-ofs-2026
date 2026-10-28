"""OFS operational map parameters (colormap, levels, titles, units).

Ported for training from ``devmetmar/ofs-plotter``
(``src/inaflows/libplotter.py`` → ``mapCollection``).

Credit: BMKG Center for Marine Meteorology / ofs-plotter maintainers.
"""

from __future__ import annotations

import matplotlib
import matplotlib.colors

_MAP_INST_CACHE: dict[str, object] = {}


def list_params() -> list[str]:
    """Return available mapCollection keys."""
    return sorted(
        [
            "swh", "ws", "wg", "mwh", "wmp", "wml", "psh", "psp", "wsh", "wsp",
            "wpp", "wpl", "csd", "csdk", "s", "st", "sl", "vv", "ww",
        ]
    )


def get_param(name: str) -> "mapCollection":
    """Load a named OFS plot parameter set (e.g. ``swh``, ``ws``, ``csd``)."""
    return mapCollection(str(name).lower())


class mapCollection:
    """
    Collection of map variables for plotter
    
    Usage:
    metapicker(param:str)
    
    Example:
    metapicker('swh')
    """
    def __new__(cls, mpick):
        key = str(mpick).lower()
        cached = _MAP_INST_CACHE.get(key)
        if cached is not None:
            return cached
        return super().__new__(cls)

    def __init__(self,mpick):
        key = str(mpick).lower()
        if key in _MAP_INST_CACHE:
            return
        mdict = {'swh' : {'color' : self.__cswh__,
                          'meta'  : self.__mswh__},
                 'ws'  : {'color' : self.__cws__,
                          'meta'  : self.__mws__},
                 'wg'  : {'color' : self.__cwg__,
                          'meta'  : self.__mwg__},
                 'mwh' : {'color' : self.__cswh__,
                          'meta'  : self.__mmwh__},
                 'wmp' : {'color' : self.__cwmp__,
                          'meta'  : self.__mwmp__},
                 'wml' : {'color' : self.__cwml__,
                          'meta'  : self.__mwml__},
                 'psh' : {'color' : self.__cswh__,
                          'meta'  : self.__mpsh__},
                 'psp' : {'color' : self.__cwmp__, #not ok
                          'meta'  : self.__mpsp__},
                 'wsh' : {'color' : self.__cswh__,
                          'meta'  : self.__mwsh__},
                 'wsp' : {'color' : self.__cwmp__, #not ok
                          'meta'  : self.__mwsp__},
                 'wpp' : {'color' : self.__cwpp__,
                          'meta'  : self.__mwpp__},
                 'wpl' : {'color' : self.__cwpl__,
                          'meta'  : self.__mwpl__},
                 'csd' : {'color' : self.__ccsd__,
                          'meta'  : self.__mcsd__},
                 'csdk' : {'color' : self.__ccsdk__,
                          'meta'  : self.__mcsdk__},
                 's'   : {'color' : self.__cs__,
                          'meta'  : self.__ms__},
                 'st'  : {'color' : self.__cst__,
                          'meta'  : self.__mst__},
                 'sl'  : {'color' : self.__csl__,
                          'meta'  : self.__msl__},
                 'vv'  : {'color' : self.__cvv__,
                          'meta'  : self.__mvv__},
                 'ww'  : {'color' : self.__cww__,
                          'meta'  : self.__mww__}}
        
        if key not in mdict:
            raise KeyError(
                f"Unknown mapCollection key {mpick!r}. "
                f"Available: {', '.join(sorted(mdict))}"
            )
        mdict[key]['color']()
        mdict[key]['meta']()
        _MAP_INST_CACHE[key] = self
    
    def __cswh__(self):
        self.clev = [0,0.5,0.75,1,1.25,1.5,2,2.5,3,3.5,4,5,6,7]
        self.extend = 'max'
        self.colorbar = ((0.0274509803921569,0.364705882352941,0.901960784313726),
                         (0.192156862745098,0.458823529411765,0.737254901960784),
                         (0.356862745098039,0.745098039215686,0.905882352941177),
                         (0.00392156862745098,0.984313725490196,0.737254901960784),
                         (0.00392156862745098,0.843137254901961,0.262745098039216),
                         (1,0.984313725490196,0.321568627450980),
                         (1,0.670588235294118,0.192156862745098),
                         (1,0.490196078431373,0.160784313725490),
                         (0.611764705882353,0.270588235294118,0.0627450980392157),
                         (0.905882352941177,0.270588235294118,0.227450980392157),
                         (0.780392156862745,0.172549019607843,0.196078431372549),
                         (0.905882352941177,0.203921568627451,0.776470588235294),
                         (0.709803921568628,0.203921568627451,0.607843137254902),
                         (0.411764705882353,0.113725490196078,0.466666666666667))
        
    def __cswhteluk__(self):
        self.clev = [0,0.125,0.25,0.375,0.5,0.625,0.75,0.875,1,1.125,1.25,1.375,1.5,1.625]
        self.extend = 'max'
        self.colorbar = ((0.0274509803921569,0.364705882352941,0.901960784313726),
                         (0.192156862745098,0.458823529411765,0.737254901960784),
                         (0.356862745098039,0.745098039215686,0.905882352941177),
                         (0.00392156862745098,0.984313725490196,0.737254901960784),
                         (0.00392156862745098,0.843137254901961,0.262745098039216),
                         (1,0.984313725490196,0.321568627450980),
                         (1,0.670588235294118,0.192156862745098),
                         (1,0.490196078431373,0.160784313725490),
                         (0.611764705882353,0.270588235294118,0.0627450980392157),
                         (0.905882352941177,0.270588235294118,0.227450980392157),
                         (0.780392156862745,0.172549019607843,0.196078431372549),
                         (0.905882352941177,0.203921568627451,0.776470588235294),
                         (0.709803921568628,0.203921568627451,0.607843137254902),
                         (0.411764705882353,0.113725490196078,0.466666666666667))
        
    def __cws__(self):
        self.clev = [0,2,4,6,8,10,15,20,25,30,35,40,50,60]
        self.extend = 'max'
        self.colorbar = ((0.776470588000000,0.921568627000000,1),
                         (0.647058824000000,0.843137255000000,0.905882353000000),
                         (0.388235294000000,0.780392157000000,0.968627451000000),
                         (0.709803922000000,1,0.741176471000000),
                         (0.223529412000000,0.890196078000000,0.419607843000000),
                         (0.709803922000000,0.874509804000000,0.450980392000000),
                         (0.937254902000000,0.858823529000000,0.419607843000000),
                         (0.968627451000000,0.729411765000000,0.450980392000000),
                         (1,0.364705882000000,0.129411765000000),
                         (0.807843137000000,0.125490196000000,0.0627450980000000),
                         (1,0.125490196000000,0.160784314000000),
                         (0.905882353000000,0.219607843000000,0.776470588000000),
                         (0.678431373000000,0.203921569000000,0.611764706000000),
                         (0.419607843000000,0.0941176470000000,0.482352941000000))

    def __cwg__(self):
        self.clev = [0,2,4,6,8,10,15,20,25,30,35,40,50,60]
        self.extend = 'max'
        self.colorbar = ((0.776470588000000,0.921568627000000,1),
                         (0.647058824000000,0.843137255000000,0.905882353000000),
                         (0.388235294000000,0.780392157000000,0.968627451000000),
                         (0.709803922000000,1,0.741176471000000),
                         (0.223529412000000,0.890196078000000,0.419607843000000),
                         (0.709803922000000,0.874509804000000,0.450980392000000),
                         (0.937254902000000,0.858823529000000,0.419607843000000),
                         (0.968627451000000,0.729411765000000,0.450980392000000),
                         (1,0.364705882000000,0.129411765000000),
                         (0.807843137000000,0.125490196000000,0.0627450980000000),
                         (1,0.125490196000000,0.160784314000000),
                         (0.905882353000000,0.219607843000000,0.776470588000000),
                         (0.678431373000000,0.203921569000000,0.611764706000000),
                         (0.419607843000000,0.0941176470000000,0.482352941000000))
        
    def __cwmp__(self):
        self.clev = [0,2,4,6,8,10,12,14,16,18,20,22,24]
        self.extend = 'max'
        self.colorbar = ((0,0.203921569000000,0.678431373000000),
                         (0,0.333333333000000,0.776470588000000),
                         (0,0.490196078000000,0.937254902000000),
                         (0,0.780392157000000,0.937254902000000),
                         (0.129411765000000,0.968627451000000,0.905882353000000),
                         (0.352941176000000,0.905882353000000,0.678431373000000),
                         (0.807843137000000,0.890196078000000,0.290196078000000),
                         (1,1,0),
                         (0.905882353000000,0.713725490000000,0.0313725490000000),
                         (0.905882353000000,0.364705882000000,0),
                         (0.870588235000000,0.109803922000000,0.0627450980000000),
                         (0.611764706000000,0.0313725490000000,0.0313725490000000),
                         (0.290196078000000,0,0))

    def __cwpp__(self):
        self.clev = [0,2,4,6,8,10,12,14,16,18,20,22,24]
        self.extend = 'max'
        self.colorbar = ((0,0.203921569000000,0.678431373000000),
                         (0,0.333333333000000,0.776470588000000),
                         (0,0.490196078000000,0.937254902000000),
                         (0,0.780392157000000,0.937254902000000),
                         (0.129411765000000,0.968627451000000,0.905882353000000),
                         (0.352941176000000,0.905882353000000,0.678431373000000),
                         (0.807843137000000,0.890196078000000,0.290196078000000),
                         (1,1,0),
                         (0.905882353000000,0.713725490000000,0.0313725490000000),
                         (0.905882353000000,0.364705882000000,0),
                         (0.870588235000000,0.109803922000000,0.0627450980000000),
                         (0.611764706000000,0.0313725490000000,0.0313725490000000),
                         (0.290196078000000,0,0))
        
    def __cwml__(self):
        self.clev = [0, 5, 10, 15, 25, 50, 75, 100, 125, 150, 200, 250, 300]
        self.extend = 'max'
        self.colorbar = ((0,0.203921569000000,0.678431373000000),
                         (0,0.333333333000000,0.776470588000000),
                         (0,0.490196078000000,0.937254902000000),
                         (0,0.780392157000000,0.937254902000000),
                         (0.129411765000000,0.968627451000000,0.905882353000000),
                         (0.352941176000000,0.905882353000000,0.678431373000000),
                         (0.807843137000000,0.890196078000000,0.290196078000000),
                         (1,1,0),
                         (0.905882353000000,0.713725490000000,0.0313725490000000),
                         (0.905882353000000,0.364705882000000,0),
                         (0.870588235000000,0.109803922000000,0.0627450980000000),
                         (0.611764706000000,0.0313725490000000,0.0313725490000000),
                         (0.290196078000000,0,0))
        
    def __cwpl__(self):
        self.clev = [0, 5, 10, 15, 25, 50, 75, 100, 125, 150, 200, 250, 300]
        self.extend = 'max'
        self.colorbar = ((0,0.203921569000000,0.678431373000000),
                         (0,0.333333333000000,0.776470588000000),
                         (0,0.490196078000000,0.937254902000000),
                         (0,0.780392157000000,0.937254902000000),
                         (0.129411765000000,0.968627451000000,0.905882353000000),
                         (0.352941176000000,0.905882353000000,0.678431373000000),
                         (0.807843137000000,0.890196078000000,0.290196078000000),
                         (1,1,0),
                         (0.905882353000000,0.713725490000000,0.0313725490000000),
                         (0.905882353000000,0.364705882000000,0),
                         (0.870588235000000,0.109803922000000,0.0627450980000000),
                         (0.611764706000000,0.0313725490000000,0.0313725490000000),
                         (0.290196078000000,0,0))
        
    def __ccsd__(self):
        self.clev = [0, 5, 10, 20, 30, 45, 60, 80, 100, 150, 200, 300, 400]
        self.extend = 'max'
        self.colorbar = ((0.0, 0.2980392156862745, 0.6),
                         (0.0, 0.5019607843137255, 1.0),
                         (0.4, 0.6980392156862745, 1.0),
                         (0.4, 1.0, 1.0),
                         (0.0, 0.9411764705882353, 0.5882352941176471),
                         (0.0, 0.8431372549019608, 0.0),
                         (0.6, 1.0, 0.043137254901960784),
                         (1.0, 1.0, 0.3137254901960784),
                         (1.0, 0.6, 0.3137254901960784),
                         (1.0, 0.5019607843137255, 0.0),
                         (0.8, 0.4, 0.0),
                         (0.8, 0.0, 0.0),
                         (0.6, 0.0, 0.0))
    
    def __ccsdk__(self):
        self.clev = [0, 0.1, 0.2, 0.4, 0.6, 0.9, 1.2, 1.6, 2, 3, 4, 6, 8]
        self.extend = 'max'
        self.colorbar = ((0.0, 0.2980392156862745, 0.6),
                         (0.0, 0.5019607843137255, 1.0),
                         (0.4, 0.6980392156862745, 1.0),
                         (0.4, 1.0, 1.0),
                         (0.0, 0.9411764705882353, 0.5882352941176471),
                         (0.0, 0.8431372549019608, 0.0),
                         (0.6, 1.0, 0.043137254901960784),
                         (1.0, 1.0, 0.3137254901960784),
                         (1.0, 0.6, 0.3137254901960784),
                         (1.0, 0.5019607843137255, 0.0),
                         (0.8, 0.4, 0.0),
                         (0.8, 0.0, 0.0),
                         (0.6, 0.0, 0.0))
        
    def __cs__(self):
        self.clev = [30,30.5,31,31.5,32,32.5,33,33.5,34,34.5,35,35.5,36]
        self.extend = 'both'
        self.colorbar = ((0.184313725000000,0.235294118000000,0.549019608000000),
                         (0.231372549000000,0.317647059000000,0.627450980000000),
                         (0.247058824000000,0.364705882000000,0.670588235000000),
                         (0.254901961000000,0.470588235000000,0.725490196000000),
                         (0.156862745000000,0.698039216000000,0.917647059000000),
                         (0.384313725000000,0.788235294000000,0.803921569000000),
                         (0.450980392000000,0.768627451000000,0.623529412000000),
                         (0.623529412000000,0.800000000000000,0.368627451000000),
                         (0.870588235000000,0.886274510000000,0.254901961000000),
                         (0.972549020000000,0.749019608000000,0.168627451000000),
                         (0.929411765000000,0.533333333000000,0.184313725000000),
                         (0.929411765000000,0.270588235000000,0.215686275000000),
                         (0.878431373000000,0.180392157000000,0.180392157000000),
                         (0.568627451000000,0.149019608000000,0.156862745000000))
    
    def __cst__(self):
        # self.clev = [16,18,20,22,24,26,28,30,32,34,36]
        self.clev = [16,18,20,22,24,26,26.5,27,27.5,28,28.5,29,29.5,30,30.5,31,31.5,32,34,36]
        self.extend = 'both'
        self.colorbar = ((0.00392156900000000,0.00392156900000000,0.941176471000000),
                         (0.274509804000000,0.356862745000000,0.988235294000000),
                         (0.282352941000000,0.627450980000000,0.980392157000000),
                         (0.0627450980000000,0.901960784000000,0.972549020000000),
                         (0.184313725000000,0.992156863000000,0.760784314000000),
                         (0.537254902000000,0.992156863000000,0.450980392000000),
                         (0.831372549000000,1,0.156862745000000),
                         (0.949019608000000,0.831372549000000,0.00784313700000000),
                         (0.909803922000000,0.666666667000000,0),
                         (0.854901961000000,0.349019608000000,0),
                         (0.933333333333333,0.0666666666666667,0.0313725490196078),
                         (0.254901960784314,0.0470588235294118,0.0627450980392157))
    
    def __csl__(self):
        self.clev = [-2,-1.75,-1.5,-1.25,-1,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1,1.25,1.5,1.75,2]
        self.extend = 'both'
        # self.colorbar = matplotlib.colormaps['bwr']
        self.colorbar = ((0.0352941180000000,0.200000000000000,0.800000000000000),
                         (0.0352941180000000,0.200000000000000,0.800000000000000),
                         (0.203921569000000,0.203921569000000,1),
                         (0.356862745000000,0.356862745000000,1),
                         (0.407843137000000,0.407843137000000,1),
                         (0.509803922000000,0.509803922000000,1),
                         (0.611764706000000,0.611764706000000,1),
                         (0.819607843000000,0.819607843000000,1),
                         # (0.972549020000000,0.972549020000000,1),
                         # (0.972549020000000,0.972549020000000,1),
                         (1,0.870588235000000,0.870588235000000),
                         (1,0.768627451000000,0.768627451000000),
                         (1,0.611764706000000,0.611764706000000),
                         (1,0.509803922000000,0.509803922000000),
                         (1,0.407843137000000,0.403921569000000),
                         (1,0.305882353000000,0.305882353000000),
                         (1,0.203921569000000,0.203921569000000),
                         (0.956862745000000,0.125490196000000,0.0117647060000000)) 

    def __cvv__(self):
        self.clev = [-2,-1.75,-1.5,-1.25,-1,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1,1.25,1.5,1.75,2]
        self.extend = 'both'
        # self.colorbar = matplotlib.colormaps['bwr']
        self.colorbar = ((0.0352941180000000,0.200000000000000,0.800000000000000),
                         (0.0352941180000000,0.200000000000000,0.800000000000000),
                         (0.203921569000000,0.203921569000000,1),
                         (0.356862745000000,0.356862745000000,1),
                         (0.407843137000000,0.407843137000000,1),
                         (0.509803922000000,0.509803922000000,1),
                         (0.611764706000000,0.611764706000000,1),
                         (0.819607843000000,0.819607843000000,1),
                         # (0.972549020000000,0.972549020000000,1),
                         # (0.972549020000000,0.972549020000000,1),
                         (1,0.870588235000000,0.870588235000000),
                         (1,0.768627451000000,0.768627451000000),
                         (1,0.611764706000000,0.611764706000000),
                         (1,0.509803922000000,0.509803922000000),
                         (1,0.407843137000000,0.403921569000000),
                         (1,0.305882353000000,0.305882353000000),
                         (1,0.203921569000000,0.203921569000000),
                         (0.956862745000000,0.125490196000000,0.0117647060000000)) 

    def __cww__(self):
        self.clev = [0, 1.25, 2.5, 4, 6, 9]
        self.extend = ''
        self.colorbar = matplotlib.colors.ListedColormap(
                        [#"#0859E7", 
                         # "#3075BD", 
                         # "#63C3E7", 
                         # "#55FBBD", 
                         # "#48D342", ijo muda
                         '#FFFFFF',
                         "#FFFB52", 
                         # "#F9AD39", cokelat muda
                         "#F7792A", 
                         # "#A54518", dark choco
                         # "#E74941", red
                         "#CE2C38",
                         "red",
                         # "#EF37CE",  
                         "#B5349C"])
        
    def __mswh__(self):
        self.savename = 'swh'
        self.datatype = 'direction'
        self.mag      = 'hs'
        self.var1     = 'hs'
        self.var2     = 'dir'
        self.figtitle = 'Significant Wave Height and Direction'
        self.cbrtitle = 'Significant Wave Height'
        self.dirtitle = 'Wave Direction'
        self.unit     = 'm'
        self.nobathid = False
        
    def __mws__(self):
        self.savename = 'ws'
        self.datatype = 'vector'
        self.mag      = 'uwnd'
        self.var1     = 'uwnd'
        self.var2     = 'vwnd'
        self.figtitle = 'Wind Speed and Direction (10m)'
        self.cbrtitle = 'Wind Speed'
        self.dirtitle = 'Wind Direction'
        self.unit     = 'knot'
        self.nobathid = False

    def __mwg__(self):
        self.savename = 'wg'
        self.datatype = 'vector'
        self.mag      = 'gust'
        self.var1     = 'uwnd'
        self.var2     = 'vwnd'
        self.figtitle = 'Wind Gust Speed and Direction (10m)'
        self.cbrtitle = 'Wind Gust Speed'
        self.dirtitle = 'Wind Gust\nDirection'
        self.unit     = 'knot'
        self.nobathid = False

    def __mmwh__(self):
        self.savename = 'mwh'
        self.datatype = 'direction'
        self.mag      = 'hmax'
        self.var1     = 'hmax'
        self.var2     = 'dir'
        self.figtitle = 'Maximum Wave Height and Direction'
        self.cbrtitle = 'Maximum Wave Height'
        self.dirtitle = 'Wave Direction'
        self.unit     = 'm'
        self.nobathid = False
        
    def __mwmp__(self):
        self.savename = 'wmp'
        self.datatype = 'direction'
        self.mag      = 't01'
        self.var1     = 't01'
        self.var2     = 'dir'
        self.figtitle = 'Mean Wave Period and Direction'
        self.cbrtitle = 'Mean Wave Period'
        self.dirtitle = 'Wave Direction'
        self.unit     = 'second'
        self.nobathid = False

    def __mwpp__(self):
        self.savename = 'wmp'
        self.datatype = 'direction'
        self.mag      = 'wpp'
        self.var1     = 'wpp'
        self.var2     = 'dir'
        self.figtitle = 'Peak Wave Period and Direction'
        self.cbrtitle = 'Peak Wave Period'
        self.dirtitle = 'Wave Direction'
        self.unit     = 'second'
        self.nobathid = False

    def __mwml__(self):
        self.savename = 'wml'
        self.datatype = 'direction'
        self.mag      = 'lm'
        self.var1     = 'lm'
        self.var2     = 'dir'
        self.figtitle = 'Wave Mean Length and Direction'
        self.cbrtitle = 'Wave Mean Length'
        self.dirtitle = 'Wave Direction'
        self.unit     = 'meter'
        self.nobathid = False
        
    def __mwpl__(self):
        self.savename = 'wpl'
        self.datatype = 'direction'
        self.mag      = 'wpl'
        self.var1     = 'wpl'
        self.var2     = 'wpd'
        self.figtitle = 'Wave Peak Length and Direction'
        self.cbrtitle = 'Wave Peak Length'
        self.dirtitle = 'Wave Direction'
        self.unit     = 'meter'
        self.nobathid = False

    def __mpsh__(self):
        self.savename = 'psh'
        self.datatype = 'direction'
        self.mag      = 'phs01'
        self.var1     = 'phs01'
        self.var2     = 'pdi01'
        self.figtitle = 'Primary Swell Height and Direction'
        self.cbrtitle = 'Primary Swell Height'
        self.dirtitle = 'Primary Swell\nDirection'
        self.unit     = 'm'
        self.nobathid = True
        
    def __mpsp__(self):
        self.savename = 'psp'
        self.datatype = 'magnitude'
        self.mag      = 'ptp01'
        self.var1     = 'ptp01'
        self.var2     = 'pdi01'
        self.figtitle = 'Primary Swell Period and Direction'
        self.cbrtitle = 'Primary Swell Period'
        self.dirtitle = 'Primary Swell\nDirection'
        self.unit     = 'second'
        self.nobathid = True
        
    def __mwsh__(self):
        self.savename = 'wsh'
        self.datatype = 'direction'
        self.mag      = 'phs00'
        self.var1     = 'phs00'
        self.var2     = 'pdi00'
        self.figtitle = 'Wind Sea Height and Direction'
        self.cbrtitle = 'Wind Sea Height'
        self.dirtitle = 'Wind Sea\nDirection'
        self.unit     = 'm'
        self.nobathid = True
        
    def __mwsp__(self):
        self.savename = 'wsp'
        self.datatype = 'magnitude'
        self.mag      = 'ptp00'
        self.var1     = 'ptp00'
        self.var2     = 'pdi00'
        self.figtitle = 'Wind sea period and Direction'
        self.cbrtitle = 'Wind sea period'
        self.dirtitle = 'Wind Sea\nDirection'
        self.unit     = 'second'
        self.nobathid = True
        
    def __mcsd__(self):
        self.savename = 'csd'
        self.datatype = 'vector'
        self.mag      = 'u'
        self.var1     = 'u'
        self.var2     = 'v'
        self.figtitle = 'Current Speed and Direction'
        self.cbrtitle = 'Current Speed'
        self.dirtitle = 'Current Direction'
        self.unit     = 'cm/s'
        self.avt      = 'Average'
        self.nobathid = True

    def __mcsdk__(self):
        self.savename = 'csd'
        self.datatype = 'vector'
        self.mag      = 'u'
        self.var1     = 'u'
        self.var2     = 'v'
        self.figtitle = 'Current Speed and Direction'
        self.cbrtitle = 'Current Speed'
        self.dirtitle = 'Current Direction'
        self.unit     = 'knot'
        self.avt      = 'Average'
        self.nobathid = True

    def __ms__(self):
        self.savename = 's'
        self.datatype = 'magnitude'
        self.mag      = 'S'
        self.var1     = 'S'
        self.var2     = 'S'
        self.figtitle = 'Salinity'
        self.cbrtitle = 'Salinity'
        self.unit     = 'PSU'
        self.avt      = 'Average'
        self.nobathid = True
        
    def __mst__(self):
        self.savename = 'st'
        self.datatype = 'magnitude'
        self.mag      = 'T'
        self.var1     = 'T'
        self.var2     = 'T'
        self.figtitle = 'Sea Temperature'
        self.cbrtitle = 'Sea Temperature'
        self.unit     = '°C'
        self.avt      = 'Average'
        self.nobathid = True
        
    def __msl__(self):
        self.savename = 'sl'
        self.datatype = 'magnitude'
        self.mag      = 'zeta'
        self.var1     = 'zeta'
        self.var2     = 'zeta'
        self.figtitle = 'Sea Surface Height'
        self.cbrtitle = 'Sea Surface Height'
        self.unit     = 'm'
        self.nobathid = True

    def __mvv__(self):
        self.savename = 'w'
        self.datatype = 'magnitude'
        self.mag      = 'w'
        self.var1     = 'w'
        self.var2     = 'w'
        self.figtitle = 'Vertical Velocity'
        self.cbrtitle = 'Vertical Velocity'
        self.unit     = 'cm/s'
        self.nobathid = True

    def __mww__(self):
        self.savename = 'ww'
        self.datatype = 'magnitude'
        self.mag      = 'hs'
        self.var1     = 'hs'
        self.var2     = 'dir'
        self.figtitle = 'Informasi Tinggi Gelombang'
        self.cbrtitle = ''
        self.dirtitle = ''
        self.unit     = 'm'
        self.nobathid = False
