#!/usr/bin/env python3

"""
An 18-regions Europe power system long-term investment model constraint by
current political decision on climate change mitigation targets.

Analyzed time range: snapshot least-cost planning for 2040
"""

import os
import pickle
from oemof.solph import OperationalModel
from oemof.outputlib import ResultsDataFrame
from europepstrans.model.constraints import emission_cap
from europepstrans.tools.io import get_cost_data, get_storage_parameter,\
    get_efficiency_parameters, get_timeseries_data, get_transmission_capacities
from europepstrans.model.tools import initialize_energysystem
from europepstrans.model.build import create_buses, create_demands,\
    create_ptg_objects, create_res_feeders, create_storages,\
    create_transformers, create_transmission


def run_3regions_example():
    # define number of periods to be computed
    periods = 2

    es = initialize_energysystem(periods=periods)

    resource_costs = {'natural_gas': 0.0282,
                      'coal': 0.0088,
                      'uranium': 0.0078}
    res_technologies = ['wind', 'solar', 'hydro']
    conv_technologies = {'ccgt': 'natural_gas',
                         'ocgt': 'natural_gas',
                         'coal': 'coal',
                         'nuclear': 'uranium'}

    storage_technologies = ['battery', 'phs']

    losses = 0.016
    co2_cap = 54797831000

    data_path = 'data'

    # obtain time series data
    data = get_timeseries_data(data_path)

    # get cost and efficiency parameters
    costs = get_cost_data('cost_parameters.csv', data_path=data_path)
    efficiencies = get_efficiency_parameters('efficiency_parameters.csv',
                                             data_path)
    storage_parameter = get_storage_parameter('storage_parameter.csv',
                                              data_path=data_path)

    trm_data = get_transmission_capacities(
        '3regions_transmission_capacities.csv',
        losses,
        data_path=data_path)

    # create model objects: buses
    buses = create_buses(['electricity'] + list(resource_costs.keys()),
                         list(data.index.get_level_values('region').unique()),
                         resource_costs)

    # create RES sources objects (time series based)
    create_res_feeders(buses, costs, data, res_technologies)

    # create conventional power plants objects
    create_transformers(buses, costs, efficiencies, conv_technologies)

    # create demand objects
    create_demands(buses, data)

    # create storage objects
    create_storages(buses, storage_parameter, storage_technologies, costs)
    create_ptg_objects(buses, efficiencies, storage_parameter, costs)

    # create grid objects
    create_transmission(buses, trm_data, costs)

    om = OperationalModel(es)

    om = emission_cap(om, es._groups, periods, co2_cap)


    om.write(os.path.join(os.path.expanduser('~'),
                                '.europepstrans',
                                'lp_files',
                                "3regions.lp"),
             io_options={'symbolic_solver_labels': True})

    om.solve(solver='gurobi',
             solve_kwargs={'tee': True},
             cmdline_options={'method': 2})

    pickle.dump(ResultsDataFrame(energy_system=es),
                open(os.path.join(os.path.expanduser('~'),
                                '.europepstrans',
                                'results',
                                "result_df.pkl"), "wb" ))


if __name__ == "__main__":

    run_3regions_example()
