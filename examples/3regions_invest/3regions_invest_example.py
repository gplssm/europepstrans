#!/usr/bin/env python3

"""
An 18-regions Europe power system long-term investment model constraint by
current political decision on climate change mitigation targets.

Analyzed time range: snapshot least-cost planning for 2040
"""

import pandas as pd
import os
import pickle
from oemof.solph import (Sink, Source, LinearTransformer, Bus, Flow,
                         OperationalModel, EnergySystem, GROUPINGS,
                         NodesFromCSV, Investment, Storage)
from oemof.outputlib import ResultsDataFrame
from europepstrans.results import TimeFrameResults
from europepstrans.results.plot import plots
from europepstrans.model.constraints import emission_cap


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

def get_timeseries_data(data_path):
    """
    Time series data such as wind power feedin and power demand

    Returns
    -------
    data: Pandas Dataframe
        Column based table with Multiindex for time, space and scenario year
    """
    #TODO: At data per scenario year, if required (such as for demand)
    #TODO: create standard data for all time series data, maybe like sequence data file with multiple headers
    demand_data_file = '3regions_demand_data.csv'
    wind_feedin_file = '3regions_wind_data.csv'
    solar_feedin_file = '3regions_solar_data.csv'
    hydro_feedin_file = '3regions_hydro_data.csv'

    # obtain an wrangle demand data
    # demand = pd.read_csv(os.path.join(data_path,demand_data_file))
    demand = pd.read_csv(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         data_path,
                         demand_data_file)))
    demand.index.names = ['timestep']
    demand.columns = [x.split('_')[0] for x in demand.columns]
    demand = demand.unstack()
    demand.index.names = ['region', 'timestep']
    demand = demand.to_frame(name='demand')

    # wind feedin data
    wind_feedin = pd.read_csv(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         data_path,
                         wind_feedin_file)))
    wind_feedin.columns = [x.split('_')[0] for x in wind_feedin.columns]
    wind_feedin = wind_feedin.unstack()
    wind_feedin.index.names = ['region', 'timestep']
    wind_feedin = wind_feedin.to_frame(name='wind')

    # solar feedin data
    solar_feedin = pd.read_csv(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         data_path,
                         solar_feedin_file)))

    solar_feedin.columns = [x.split('_')[0] for x in solar_feedin.columns]
    solar_feedin = solar_feedin.unstack()
    solar_feedin.index.names = ['region', 'timestep']
    solar_feedin = solar_feedin.to_frame(name='solar')

    # hydro feedin data
    hydro_feedin = pd.read_csv(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         data_path,
                         hydro_feedin_file)))
    hydro_feedin.columns = [x.split('_')[0] for x in hydro_feedin.columns]
    hydro_feedin = hydro_feedin.unstack()
    hydro_feedin.index.names = ['region', 'timestep']
    hydro_feedin = hydro_feedin.to_frame(name='hydro')

    #  join time series data
    data = pd.concat([wind_feedin, demand, solar_feedin, hydro_feedin], axis=1)

    return data


def create_buses(labels, regions, costs, excess={'electricity': True}):
    """
    Buses are instantiated

    For each region specified a bus for each label is instantiated. If
    excess is set True, an excess term is defined for according bus label.

    Fossil resources have a global bus. This is created only if bus labels
    match one of the following labels 'natural_gas', 'coal', 'uranium'.

    Parameters
    ----------
    labels : list
        Specify bus names
    regions : list
        Regions that are considered in the model
    excess : dict of boolean, default {'electricity': True}
    costs : dict
        Cost associated with global resources per unit

    Returns
    -------
    buses : dict
        Holds structured all bus objects, accessible by buses['region']['bus']
    """
    global_buses = ['natural_gas', 'coal', 'uranium']


    buses = {}
    buses['global'] = {}

    # create global sources for resources
    for bus in labels:
        if bus in global_buses:
            buses['global'][bus] = Bus(label='_'.join([bus, 'bus']))
            Source(label='_'.join([bus, 'source']), outputs={buses['global'][bus]: Flow(
                variable_costs=costs[bus])})

    # create buses per region
    for region in regions:
        buses[region] = {}
        for bus in labels:
            buses[region][bus] = Bus(label='_'.join([bus, region]))

            # create excess component for excess production
            if excess.get(bus, None) is True:
                Sink(label='_'.join(['excess', bus, region]),
                     inputs={buses[region][bus]: Flow()})

            # connect global and regional buses
            if bus in global_buses:
                LinearTransformer(
                    label='_'.join([bus, 'global', region]),
                    inputs={buses['global'][bus]: Flow()},
                    outputs={buses[region][bus]: Flow()},
                    conversion_factors={buses[region][bus]: 1})

    return buses


def create_res_feeders(buses, costs, data, technologies, regions=None):
    """
    Instatiate RES technologies source objects (time series based)

    If list of regions is not provided keys of buses dict are applied

    Parameters
    ----------
    buses : dict
        Container for bus objects
    costs : DataFrame
        Cost data of RES technologies
    data : DataFrame
        Time series data
    technologies : list
        RES technologies with time series basis
    regions : list, optional
        Regions RES technologies objects will be created.

    Returns
    -------
    None
    """

    if regions == None:
        regions = [x for x in list(buses.keys()) if x is not 'global']

    # create fixed source object for RES technologies
    for region in regions:
        for tech in technologies:
            # TODO: add existing capacity as nominal value
            Source(label='_'.join([tech, region]),
                   outputs={buses[region]['electricity']: Flow(
                       actual_value=data.loc[region][tech],
                       variable_costs=costs.loc[tech, 'opex_var'],
                       investment=Investment(ep_costs=costs.loc[tech, 'epc'] +
                                                      costs.loc[
                                                          tech, 'opex_fix']),
                   fixed=True)})

def create_transformers(buses, costs, efficiencies, technologies, regions=None):
    """
    Instantiate transformer objects representing conventional power plants

    If list of regions is not provided keys of buses dict are applied

    Parameters
    ----------
    buses : dict
        Container for bus objects
    costs : DataFrame
        Cost data of RES technologies
    efficiencies : DataFrame
        Efficiency parameters of conventional technologies
    technologies: dict
        Power plant technologies as key and according fuel as value
    regions : list, optional
        Regions RES technologies objects will be created.

    Returns
    -------
    None
    """
    if regions == None:
        regions = [x for x in list(buses.keys()) if x is not 'global']

    # create fixed source object for RES technologies
    for region in regions:
        for tech, fuel in technologies.items():
            LinearTransformer(
                label='_'.join([tech, 'pp', region]),
                inputs={buses[region][fuel]: Flow()},
                outputs={buses[region]['electricity']: Flow(
                    variable_costs=costs.loc[tech, 'opex_var'],
                    investment=Investment(ep_costs=costs.loc[tech, 'epc'] +
                                                   costs.loc[tech, 'opex_fix'])
                )},
                conversion_factors={
                    buses[region]['electricity']:
                                        efficiencies.loc[tech]['conversion_factor']}
            )


def create_demands(buses, data, regions=None):
    """
    Instantiate demand objects in each region

    Parameters
    ----------
    buses : dict
        Container for bus objects
    data : DataFrame
        Time series data
    regions : list, optional
        Regions demand objects will be created for

    Returns
    -------
    None
    """
    if regions == None:
        regions = data.index.get_level_values('region').unique()

    for region in regions:
        Sink(label='_'.join(['demand', region]),
             inputs={buses[region]['electricity']: Flow(
                 actual_value=data.loc[region]['demand'],
                 fixed=True,
                 nominal_value=1)})


def create_transmission(buses, trm_data, costs):
    """
    Instantiate transmission capacity objects

    Parameters
    ----------
    buses : dict
        Container for bus objects
    trm_data : DataFrame
        Transmission capacity data

    Returns
    -------
    None
    """
    for it, row in trm_data.iterrows():
        LinearTransformer(
            label=row['name'],
            inputs={buses[row['from_region']]['electricity']: Flow()},
            outputs={buses[row['to_region']]['electricity']: Flow(
                variable_costs=costs.loc['trm', 'opex_var'],
                investment=Investment(ep_costs=costs.loc['trm', 'epc'] +
                                                   costs.loc['trm', 'opex_fix']))},
            conversion_factors={buses[row['to_region']]['electricity']: 1 - row['losses']}
        )


def create_storages(buses, parameter, technologies, costs, regions=None):
    """
    Create storage technology objects

    Parameters
    ----------
    buses : dict
        Container for bus objects
    parameter : DataFrame
        Parameter to model storages
    technologies: dict
        Power plant technologies as key and according fuel as value
    costs : DataFrame
        Cost data of various technologies

    Returns
    -------
    None
    """

    if regions == None:
        regions = [x for x in list(buses.keys()) if x is not 'global']

    for region in regions:
        for tech in technologies:

            # create storage transformer object for storage
            Storage(
                label='_'.join([tech, region]),
                inputs={buses[region]['electricity']: Flow(
                    variable_costs=costs.loc[tech, 'opex_var'])},
                outputs={buses[region]['electricity']: Flow(
                    variable_costs=costs.loc[tech, 'opex_var'])},
                capacity_loss=parameter.loc[tech, 'capacity_loss'],
                initial_capacity=0,
                nominal_input_capacity_ratio=1 / parameter.loc[
                    tech, 'energy_power_ratio_in'],
                nominal_output_capacity_ratio=(1 / parameter.loc[
                    tech, 'energy_power_ratio_out']),
                inflow_conversion_factor=parameter.loc[tech, 'efficiency_in'],
                outflow_conversion_factor=parameter.loc[tech, 'efficiency_out'],
                investment=Investment(ep_costs=costs.loc[tech, 'epc'] +
                                               costs.loc[tech, 'opex_fix']),
            )

def create_ptg_objects(buses, efficiencies, storage_parameter, costs,
                       regions=None):
    """
    Create objects decribing Power-to-Gas system

    Power-to-Gas (PtG) system consists of
      * Electrolysis and methanation unit aggregated in one component
      * SNG (synthetic natural gas) bus
      * Gas storage connected to SNG bus
      * Transformer with eta=1 from SNG to natural_gas bus

    Parameters
    ----------
    buses : dict
        Container for bus objects
    efficiencies : DataFrame
        Efficiency parameters of conventional technologies and PtG
    storage_parameter: DataFrame
        Parameter to model storages
    costs : DataFrame
        Cost data of various technologies
    regions : list, optional
        Regions RES technologies objects will be created.

    Returns
    -------
    buses : dict
        Container for bus objects extended by SNG bus
    """
    tech = 'ptg'
    bus = 'sng'
    storage = 'gas'

    if regions == None:
        regions = [x for x in list(buses.keys()) if x is not 'global']

    for region in regions:
        # add sng bus to buses container
        buses[region][bus] = Bus(label='_'.join([bus, region]))

        # add ptg transformer form electricity to sng
        LinearTransformer(
            label='_'.join([tech, region]),
            inputs={buses[region]['electricity']: Flow()},
            outputs={buses[region][bus]: Flow(
                variable_costs=costs.loc[tech, 'opex_var'],
                investment=Investment(ep_costs=costs.loc[tech, 'epc'] +
                                               costs.loc[tech, 'opex_fix'])
            )},
            conversion_factors={
                buses[region][bus]:
                    efficiencies.loc[tech]['conversion_factor']}
        )

        # add ideal transformer from sng to natural_gas
        LinearTransformer(
            label='_'.join(['sng2natural_gas', region]),
            inputs={buses[region][bus]: Flow()},
            outputs={buses[region]['natural_gas']: Flow(
                investment=Investment(ep_costs=0))},
            conversion_factors={
                buses[region]['natural_gas']: 1}
        )

        # add gas storage at sng bus
        Storage(
            label='_'.join([storage, region]),
            inputs={buses[region][bus]: Flow(
                variable_costs=costs.loc[storage, 'opex_var'])},
            outputs={buses[region][bus]: Flow(
                variable_costs=costs.loc[storage, 'opex_var'])},
            capacity_loss=storage_parameter.loc[storage, 'capacity_loss'],
            initial_capacity=0,
            nominal_input_capacity_ratio=1 / storage_parameter.loc[
                storage, 'energy_power_ratio_in'],
            nominal_output_capacity_ratio=(1 / storage_parameter.loc[
                storage, 'energy_power_ratio_out']),
            inflow_conversion_factor=storage_parameter.loc[storage, 'efficiency_in'],
            outflow_conversion_factor=storage_parameter.loc[storage, 'efficiency_out'],
            investment=Investment(ep_costs=costs.loc[storage, 'epc'] +
                                           costs.loc[storage, 'opex_fix']),
        )

def epc(capex, wacc, lifetime):
    """
    Equivalent periodical costs (if periode is one year: equivalent annual
    costs.

    Parameters
    ----------
    capex : numeric
        Capital expenditure per unit (kW)
    wacc : numeric
        Weighted average cost of capital
    lifetime : numeric
        Nominal expected lifetime of technology

    Returns
    -------
    epc : numeric
        Equivalent periodical costs
    """
    epc = capex * (wacc * (1 + wacc) ** lifetime) / (
        (1 + wacc) ** lifetime - 1)

    return epc


def get_cost_data(file_name, data_path=''):
    """
    Read cost data from file and calculate required parameters

    Parameters
    ----------
    file_name : str
        Name of cost parameter file

    Returns
    -------
    costs : DataFrame
        Cost parameters for technologies
    """

    # read cost parameters file
    costs = pd.read_csv(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         data_path,
                         file_name)),
            index_col='technology')


    # TODO: approve calculation of epc: should basically be the same as
    # TODO: capex * crf

    costs['epc'] = epc(costs['capex'],
                       costs['wacc'],
                       costs['lifetime'])

    return costs


def get_efficiency_parameters(file_name, data_path=''):
    """
    Read efficiency parameters from file

    Parameters
    ----------
    file_name : str
        Name of cost parameter file

    Returns
    -------
    efficiencies : DataFrame
        Efficiency parameters for technologies
    """

    # read efficiency parameters file
    efficiencies = pd.read_csv(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         data_path,
                         file_name)),
            index_col='technology')

    return efficiencies

def get_storage_parameter(file_name, data_path=''):
    """
    Read storage parameters from file

    Parameters
    ----------
    file_name : str
        Name of storage parameter file

    Returns
    -------
    storage_parameter : DataFrame
        Efficiency parameters for technologies
    """

    # read efficiency parameters file
    storage_parameter = pd.read_csv(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         data_path,
                         file_name)),
            index_col='technology')

    return storage_parameter


def get_transmission_capacities(file_name, losses, data_path=''):
    """
    Retrieve transmission capacity data

    Additionally losses parameter is added to DataFrame

    Parameters
    ----------
    file_name : str
        File name of transmission capacity data (in CSV)
    losses : numeric
        Relative losses per 100 km

    Returns
    -------
    trm_data : DataFrame
        Transmission capacity data
    """
    # read efficiency parameters file
    trm_data = pd.read_csv(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         data_path,
                         file_name)))

    trm_data['losses'] = trm_data['length'] * losses / 100

    return trm_data

def run_3regions_example():
    # define number of periods to be computed
    periods = 744

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
