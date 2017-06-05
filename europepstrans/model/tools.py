from oemof.solph import EnergySystem, GROUPINGS
import pandas as pd

def initialize_energysystem(periods=8760):
    """
    Initialize energy system

    Parameters
    ----------
    Returns
    -------
    EnergySystem: oemof EnergySystem object
        Container for topology, sectoral coverage, etc. of energy system model
    """

    datetimeindex = pd.date_range('1/1/2012', periods=periods, freq='H')

    return EnergySystem(groupings=GROUPINGS, time_idx=datetimeindex)