import os
import pandas as pd



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
                         os.pardir,
                         os.pardir,
                         'examples',
                         '3regions_invest',
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
                         os.pardir,
                         os.pardir,
                         'examples',
                         '3regions_invest',
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
                         os.pardir,
                         os.pardir,
                         'examples',
                         '3regions_invest',
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
                         os.pardir,
                         os.pardir,
                         'examples',
                         '3regions_invest',
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
                         os.pardir,
                         os.pardir,
                         'examples',
                         '3regions_invest',
                         data_path,
                         file_name)))

    trm_data['losses'] = trm_data['length'] * losses / 100

    return trm_data


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