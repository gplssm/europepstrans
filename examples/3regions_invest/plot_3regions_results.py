#!/usr/bin/env python3

from europepstrans.results import TimeFrameResults
from europepstrans.results.plot import plots
from oemof.solph import EnergySystem
import os

def three_regions_results():
    dpath = os.path.join(os.path.expanduser('~'), '.europepstrans', 'results')
    results_file = 'result_df.pkl'

    es = EnergySystem()

    es.restore(dpath=dpath, filename=results_file)


    results = TimeFrameResults(energy_system=es)

    plots(results)

if __name__ == '__main__':
    three_regions_results()
