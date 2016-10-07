#!/usr/bin/env python3

"""
An 18-regions Europe power system long-term investment model constraint by
current political decision on climate change mitigation targets.

Analyzed time range: from now until 2050
"""

import pandas as pd
import os
from oemof.solph import (Sink, Source, LinearTransformer, Bus, Flow,
                         OperationalModel, EnergySystem, GROUPINGS,
                         NodesFromCSV, Investment)


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
    hydro_feedin_file = '3regions_wind_data.csv'

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
                                                  costs.loc[tech, 'opex_fix']))})


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
        pass
        LinearTransformer(
            label=row['name'],
            inputs={buses[row['from_region']]['electricity']: Flow()},
            outputs={buses[row['to_region']]['electricity']: Flow(
                variable_costs=costs.loc['trm', 'opex_var'],
                investment=Investment(ep_costs=costs.loc['trm', 'epc'] +
                                                   costs.loc['trm', 'opex_fix']))},
            conversion_factors={buses[row['to_region']]['electricity']: 1 - row['losses']}
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

    resource_costs = {'natural_gas': 0.03,
                      'coal': 0.01,
                      'uranium': 0.2}
    res_technologies = ['wind', 'solar', 'hydro']
    conv_technologies = {'ccgt': 'natural_gas',
                         'ocgt': 'natural_gas',
                         'coal': 'coal',
                         'nuclear': 'uranium'}
    losses = 0.01

    data_path = 'data'

    # obtain time series data
    data = get_timeseries_data(data_path)

    # get cost and efficiency parameters
    costs = get_cost_data('cost_parameters.csv', data_path=data_path)
    efficiencies = get_efficiency_parameters('efficiency_parameters.csv',
                                             data_path)
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

    # create grid objects
    create_transmission(buses, trm_data, costs)

    om = OperationalModel(es)

    om.solve(solver='gurobi',
             solve_kwargs={'tee': True},
             cmdline_options={'method': 2})

    es.dump(dpath=os.path.join(os.path.expanduser('~'),
                                '.europepstrans',
                                'results'),
             filename='result_df.pkl')


if __name__ == "__main__":
    run_3regions_example()