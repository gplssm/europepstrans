from pyomo.core import Constraint


def emission_cap(om, groups, periods, cap):

    # define co2 emissions
    #TODO: get data from csv in futures
    co2_eq = {'coal': 0.361,
              'natural_gas': 0.204}

    expr = sum(om.flow._data[tuple([groups['_'.join([tech, 'source'])],
                                    groups['_'.join([tech, 'bus'])],
                                    t])] * co2_eq[tech]
               for tech in list(co2_eq.keys())
               for t in range(0, periods)) <= cap

    om.co2_cap = Constraint(expr=expr)

    return om