"""
File contains class to run transformation path power system analyses
"""

import pandas as pd
import logging


class TransformationPathway:
    """

    """

    def __init__(self, **kwargs):
        """
        Build an instance of an transformation pathway model. You can provide
        data straightforard via **kwargs.

        Arguments
        ---------
        **kwargs: Dictionary of arbitrary keyword arguments. Possible inputs
            are
             * initial_capacity - pandas DataFrame

        Notes
        -----
        initial_capacity must by filename given as relative or absolute path. It
        has to contain following headers
         * technology
         * region
         * decommissioning_year
         * capacity

        Be aware, it is planned to change style of capacity input to supply
        the commissioning year instead of the planned year of decommission as
        this includes assumptions on lifetime. This parameter is/ should be
        declared elsewhere.

        """

        if isinstance(kwargs.get('initial_capacity', None), str):
            self.initial_capacity = self.read_initial_capacity_from_file(
                filename=kwargs['initial_capacity'])
        else:
            logging.warning('Initial capacities are not supplied. Will be'
                            'assumed as to be zero')

    def read_initial_capacity_from_file(self, filename=None):
        """
        Read capacity data from csv and returns as multiindex DataFrame

        Parameters
        ----------
        filename: str
            Filename of capacity data including it's path

        Returns
        -------
        capacity: pandas DataFrame
        """

        return pd.read_csv(filename, index_col=['technology', 'region'])



