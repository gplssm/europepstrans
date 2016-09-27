#!/usr/bin/env python3

"""
An 18-regions Europe power system long-term investment model constraint by
current political decision on climate change mitigation targets.

Analyzed time range: from now until 2050
"""

import pandas as pd
# import sys
# sys.path.remove('/home/guido/rli_home/git-repos/oemof.db')
from oemof.solph import (Sink, Source, LinearTransformer, Bus, Flow,
                         OperationalModel, EnergySystem, GROUPINGS,
                         NodesFromCSV, Investment)
import os


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

def get_timeseries_data():
    """
    Time series data such as wind power feedin and power demand

    Returns
    -------
    data: Pandas Dataframe
        Column based table with Multiindex for time, space and scenario year
    """





if __name__ == "__main__":
    es = initialize_energysystem(periods=10)

    # TODO: does excess necessarily has to have var cost? (see nodes file)

    data_path = 'data'
    nodes_flows = 'example_3regions_invest.csv'
    nodes_flows_sequences = '3regions_invest_example_seq.csv'

    nodes = NodesFromCSV(file_nodes_flows=os.path.join(
                         data_path, nodes_flows),
                     file_nodes_flows_sequences=os.path.join(
                         data_path, nodes_flows_sequences),
                        delimiter=',')
    # investment=solph.Investment(ep_costs=epc)
    for reg in ['DEU', 'XFRA', 'XBNL']:
        es.groups[reg + '_pp_gas'].investment = Investment(ep_costs=3800)

    om = OperationalModel(es)

    om.solve(solver='cbc', solve_kwargs={'tee': True})
    print(es)
