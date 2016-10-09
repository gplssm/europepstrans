from matplotlib import pyplot as plt
import os


def plots(results):

    # define colors
    cdict = {'wind': '#6495ED'.upper(),
             'solar': '#ffde32'.upper(),
             'storage': '#42c77a'.upper(),
             'ccgt_pp': '#5F9EA0'.upper(),
             'ocgt_pp': '#3278A0'.upper(),
             'coal_pp': '#8B4513'.upper(),
             'nuclear_pp': '#CD6889'.upper(),
             'hydro': '#191970'.upper(),
             'demand': '#ce4aff'.upper(),
             'excess_electricity': '#555555'.upper(),
             'battery': '#FF8C00',
             'ptg': '#C0FF3E',
             'phs': '#C76114',
             'gas': '#808000',
             'trm': '#708090'}

    barorder = ['nuclear_pp',
                  'ccgt_pp',
                  'coal_pp',
                  'ocgt_pp',
                  'hydro',
                  'wind',
                  'solar',
                  'phs',
                  'battery']

    stacked_bar_line_graph(results, cdict, barorder)

    generation_sums(results, cdict, barorder)


def stacked_bar_line_graph(results, cdict, barorder):
    group_list = ['bus_label', 'obj_label', 'type', 'datetime']


    wo_transmission = results.data[
        ~results.data.index.get_level_values('obj_label').str.contains('-')]

    # TODO: in future don't override `results.data`
    # group results to components, remove regional disaggregation
    results.data = results.data.reset_index(group_list).groupby(
        by=group_list).sum()

    # reorder and resort levels
    level_order = ['bus_label', 'type', 'obj_label', 'datetime']
    results.data = results.data.reorder_levels(level_order)
    results.data.sort_index(inplace=True)

    # Plotting a combined stacked plot
    fig = plt.figure(figsize=(24, 14))
    plt.rc('legend', **{'fontsize': 19})
    plt.rcParams.update({'font.size': 19})
    plt.style.use('grayscale')

    handles, labels = results.io_plot(
        bus_label='electricity',
        cdict=cdict,
        barorder=barorder,
        lineorder=['demand', 'battery', 'phs', 'ptg','excess_electricity'],
        line_kwa={'linewidth': 4},
        ax=fig.add_subplot(1, 1, 1),
        date_from="2012-01-01 00:00:00",
        date_to="2012-01-31 23:00:00", )

    results.ax.set_ylabel('Power in kW')
    results.ax.set_xlabel('Date')
    results.ax.set_title("Hourly balance of electricity system")
    results.set_datetime_ticks(tick_distance=168, date_format='%d-%m-%Y')
    results.outside_legend(handles=handles, labels=labels)

    plt.savefig(os.path.join(os.path.expanduser('~'),
                                '.europepstrans',
                                'figures',
                                "3regions_stacked_io.png"))


def generation_sums(results, cdict, barorder):
    results.data.sum(level='obj_label').loc[barorder].plot(kind='bar', stacked=True)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.expanduser('~'),
                                '.europepstrans',
                                'figures',
                                "3regions_generation.png"))
