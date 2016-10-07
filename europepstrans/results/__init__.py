"""
TimeFrameResults steals methods from oemof.outputlib adapted to the structure
applied here. Most relevant difference is results data stored in self.data

"""

from oemof.outputlib import DataFramePlot

import pickle
from matplotlib import pyplot as plt
import logging
import pandas as pd


class TimeFrameResults:
    """
    Container for results of one time frame (i.e. one year)

    Attributes
    ----------
    data : DataFrame
        Structure multi-indexed result data

    """

    def __init__(self, **kwargs):
        """
        Initializes data object based on oemof results class
        """

        results_file = kwargs.get('results_file', None)
        subset = kwargs.get('subset', None)
        self.ax = kwargs.get('ax')

        if results_file is None:
            self.data = DataFramePlot(energy_system=kwargs.get('energy_system'))
        else:
            self.data = pickle.load(open(results_file, 'rb'))

        self.reformat_data()

    def preview(self):
        """
        Print short preview of data
        """
        return self.data.head()

    def reformat_data(self):
        """
        Extract region information from bus label put into separate index label
        """
        # TODO: get regions list from elsewhere
        regions = ['deu', 'xfra', 'xbnl']
        regions_leading_underscore = ['_' + x for x in regions]

        # put bus_label to column (required to work on)
        self.data.reset_index(level='bus_label', inplace=True)
        self.data.reset_index(level='obj_label', inplace=True)

        # extra region from bus label and write to new column
        self.data['region'] = self.data['bus_label'].str.extract(
            r"(?=(" + '|'.join(regions) + r"))", expand=True)
        self.data['region'].fillna('global', inplace=True)

        # remove region from bus_label and obj_label
        self.data['bus_label'] = self.data['bus_label'].str.replace(
            r"(" + '|'.join(regions_leading_underscore) + r")", '')
        self.data['obj_label'] = self.data['obj_label'].str.replace(
            r"(" + '|'.join(regions_leading_underscore) + r")", '')

        # put bus_label back to index
        self.data = self.data.set_index(['bus_label', 'region', 'obj_label'],
                                        append=True)

        # reorder and resort levels
        level_order = ['bus_label', 'type', 'obj_label', 'region', 'datetime']
        self.data = self.data.reorder_levels(level_order)

    def slice_by(self, **kwargs):
        r""" Method for slicing the ResultsDataFrame. A subset is returned.

        Parameters
        ----------
        bus_label : string
        type : string (to_bus/from_bus/other)
        obj_label: string
        date_from : string
            Start date selection e.g. "2016-01-01 00:00:00". If not set, the
            whole time range will be plotted.
        date_to : string
            End date selection e.g. "2016-03-01 00:00:00". If not set, the
            whole time range will be plotted.

        """
        kwargs.setdefault('bus_label', slice(None))
        kwargs.setdefault('type', slice(None))
        kwargs.setdefault('obj_label', slice(None))
        kwargs.setdefault(
            'date_from', self.data.index.get_level_values('datetime')[0])
        kwargs.setdefault(
            'date_to', self.data.index.get_level_values('datetime')[-1])

        # slicing
        idx = pd.IndexSlice

        subset = self.data.loc[idx[
            kwargs['bus_label'],
            kwargs['type'],
            kwargs['obj_label'],
            slice(pd.Timestamp(kwargs['date_from']),
                  pd.Timestamp(kwargs['date_to']))], :]

        return subset

    def slice_unstacked(self, unstacklevel='obj_label',
                        formatted=False, **kwargs):
        r"""Method for slicing the ResultsDataFrame. An unstacked
        subset is returned.

        Parameters
        ----------
        unstacklevel : string (default: 'obj_label')
            Level to unstack the subset of the DataFrame.
        formatted : boolean
            missing...
        """
        subset = self.slice_by(**kwargs)
        subset = subset.unstack(level=unstacklevel)
        if formatted is True:
            subset.reset_index(level=['bus_label', 'type'], drop=True,
                               inplace=True)
        # user standard insteadt of multi-indexed columns
        subset.columns = subset.columns.get_level_values(1).unique()
        # return subset
        self.subset = subset


    def plot(self, **kwargs):
        r""" Passing the data attribute to the pandas plotting method. All
        parameters will be directly passed to pandas.DataFrame.plot(). See
        http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.plot.html
        for more information.

        Returns
        -------
        self
        """
        self.ax = self.subset.plot(**kwargs)
        return self


    def io_plot(self, bus_label, cdict, line_kwa=None, lineorder=None,
                bar_kwa=None, barorder=None, **kwargs):
        r""" Plotting a combined bar and line plot to see the fitting of in-
        and outcomming flows of a bus balance.

        Parameters
        ----------
        bus_label : string
            Uid of the bus to plot the balance.
        cdict : dictionary
            A dictionary that has all possible components as keys and its
            colors as items.
        line_kwa : dictionary
            Keyword arguments to be passed to the pandas line plot.
        bar_kwa : dictionary
            Keyword arguments to be passed to the pandas bar plot.
        lineorder : list
            Order of columns to plot the line plot
        barorder : list
            Order of columns to plot the bar plot

        Note
        ----
        Further keyword arguments will be passed to the
        :class:`slice_unstacked method <DataFramePlot.slice_unstacked>`.

        Returns
        -------
        handles, labels
            Manipulated labels to correct the unsual construction of the
            stack line plot. You can use them for further maipulations.
        """
        self.ax = kwargs.get('ax', self.ax)

        if bar_kwa is None:
            bar_kwa = dict()
        if line_kwa is None:
            line_kwa = dict()

        if self.ax is None:
            fig = plt.figure()
            self.ax = fig.add_subplot(1, 1, 1)

        # Create a bar plot for all input flows
        self.slice_unstacked(bus_label=bus_label, type='to_bus', **kwargs)

        if barorder is not None:
            self.rearrange_subset(barorder)

        self.subset.plot(kind='bar', linewidth=0, stacked=True, width=1,
                         ax=self.ax, color=self.color_from_dict(cdict),
                         **bar_kwa)

        # Create a line plot for all output flows
        self.slice_unstacked(bus_label=bus_label, type='from_bus', **kwargs)
        if lineorder is not None:
            self.rearrange_subset(lineorder)
        # The following changes are made to have the bottom line on top layer
        # of all lines. Normally the bottom line is the first line that is
        # plotted and will be on the lowest layer. This is difficult to read.
        new_df = pd.DataFrame(index=self.subset.index)
        n = 0
        tmp = 0
        for col in self.subset.columns:
            if n < 1:
                new_df[col] = self.subset[col]
            else:
                new_df[col] = self.subset[col] + tmp
            tmp = new_df[col]
            n += 1
        if lineorder is None:
            new_df.sort_index(axis=1, ascending=False, inplace=True)
        else:
            lineorder.reverse()
            new_df = new_df[lineorder]
        colorlist = self.color_from_dict(cdict)
        if isinstance(colorlist, list):
            colorlist.reverse()
        separator = len(colorlist)
        new_df.plot(kind='line', ax=self.ax, color=colorlist,
                    drawstyle='steps-mid', **line_kwa)

        # Adapt the legend to the new oder
        handles, labels = self.ax.get_legend_handles_labels()
        tmp_lab = [x for x in reversed(labels[0:separator])]
        tmp_hand = [x for x in reversed(handles[0:separator])]
        handles = tmp_hand + handles[separator:]
        labels = tmp_lab + labels[separator:]
        labels.reverse()
        handles.reverse()

        self.ax.legend(handles, labels)
        return handles, labels

    def rearrange_subset(self, order):
        r"""
        Change the order of the subset DataFrame

        Parameters
        ----------
        order : list
            New order of columns

        Returns
        -------
        self
        """
        cols = list(self.subset.columns.values)
        neworder = [x for x in list(order) if x in set(cols)]
        missing = [x for x in list(cols) if x not in set(order)]
        if len(missing) > 0:
            logging.warning(
                "Columns that are not part of the order list are removed: " +
                str(missing))
        self.subset = self.subset[neworder]

    def color_from_dict(self, colordict):
        r""" Method to convert a dictionary containing the components and its
        colors to a color list that can be directly useed with the color
        parameter of the pandas plotting method.

        Parameters
        ----------
        colordict : dictionary
            A dictionary that has all possible components as keys and its
            colors as items.

        Returns
        -------
        list
            Containing the colors of all components of the subset attribute
        """
        tmplist = list(
            map(colordict.get, list(self.subset.columns)))
        tmplist = ['#00FFFF' if v is None else v for v in tmplist]
        if len(tmplist) == 1:
            colorlist = tmplist[0]
        else:
            colorlist = tmplist
        return colorlist

    def set_datetime_ticks(self, tick_distance=None, number_autoticks=3,
                           date_format='%d-%m-%Y %H:%M'):
        r""" Set configurable ticks for the time axis. One can choose the
        number of ticks or the distance between ticks and the format.

        Parameters
        ----------
        tick_distance : real
            The disctance between to ticks in hours. If not set autoticks are
            set (see number_autoticks).
        number_autoticks : int (default: 3)
            The number of ticks on the time axis, independent of the time
            range. The higher the number of ticks is, the shorter should be the
            date_format string.
        date_format : string (default: '%d-%m-%Y %H:%M')
            The string to define the format of the date and time. See
            https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
            for more information.
        """
        dates = self.subset.index.get_level_values('datetime').unique()
        if tick_distance is None:
            tick_distance = int(len(dates) / number_autoticks) - 1
        self.ax.set_xticks(range(0, len(dates), tick_distance),
                           minor=False)
        self.ax.set_xticklabels(
            [item.strftime(date_format)
             for item in dates.tolist()[0::tick_distance]],
            rotation=0, minor=False)

    def outside_legend(self, reverse=False, plotshare=0.9, **kwargs):
        r""" Move the legend outside the plot. Bases on the ideas of Joe
        Kington. See
        http://stackoverflow.com/questions/4700614/how-to-put-the-legend-out-of-the-plot
        for more information.

        Parameters
        ----------
        reverse : boolean (default: False)
            Print out the legend in reverse order. This is interesting for
            stack-plots to have the legend in the same order as the stacks.
        plotshare : real (default: 0.9)
            Share of the plot area to create space for the legend (0 to 1).
        loc : string (default: 'center left')
            Location of the plot.
        bbox_to_anchor : tuple (default: (1, 0.5))
            Set the anchor for the legend.
        ncol : integer (default: 1)
            Number of columns of the legend.
        handles : list of handles
            A list of handels if they are already modified by another function
            or method. Normally these handles will be automatically taken from
            the artis object.
        lables : list of labels
            A list of labels if they are already modified by another function
            or method. Normally these handles will be automatically taken from
            the artis object.
        Note
        ----
        All keyword arguments (kwargs) will be directly passed to the
        matplotlib legend class. See
        http://matplotlib.org/api/legend_api.html#matplotlib.legend.Legend
        for more parameters.
        """
        kwargs.setdefault('loc', 'center left')
        kwargs.setdefault('bbox_to_anchor', (1, 0.5))
        kwargs.setdefault('ncol', 1)
        handles = kwargs.pop('handles', self.ax.get_legend_handles_labels()[0])
        labels = kwargs.pop('labels', self.ax.get_legend_handles_labels()[1])

        if reverse:
            handles.reverse()
            labels.reverse()

        box = self.ax.get_position()
        self.ax.set_position([box.x0, box.y0, box.width * plotshare,
                              box.height])

        self.ax.legend(handles, labels, **kwargs)


if __name__ == '__main__':
    pass