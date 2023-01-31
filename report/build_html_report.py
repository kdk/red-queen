from pathlib import Path
from functools import reduce
from collections import defaultdict

import matplotlib.pyplot as plt
plt.style.use('ggplot')

import numpy as np
from matplotlib import ticker as mticker

from loader import load_benchmarks

OVERVIEW_PYTHON_VERSION='3.9'
OVERVIEW_HARDWARE_DESCRIPTION=None

# Read in all found JSON files
raw_benchmark_data = list(load_benchmarks(Path('./results/')))

# Munge existing JSON in to data structure we want for the plots
# Make a nestable dict, we'll store arrays at the bottom.
autoviv = lambda: defaultdict(autoviv)
benchmark_data = autoviv()

# Want a datastructure that looks like:
# benchmarks = [ {
#   display_name: 'Benchmark 1',
#   category: 'synthetic',
#   use_log: False,
#   metrics: [{display_name: 'CX count', key_: 'cx', use_log: False}, {display_name: 'compile time', key_: 'timings', use_log: True}],
#   results: {
#    $python_version[float]: {
#       $hw_descr[str]: {
#         $tool[str]: {
#           $tool_ver[float]: {
#                $algorithm[str]: {
#                   $instance[str, float]: {
#                      $metric: [ ]

NEWEST_QISKIT_VERSION = '0.0.0'

# N.B. Newer benchmark runs will overwrite earlier.
for raw in raw_benchmark_data:
    if 'mapping' in raw['id']:
        display_name = 'Revlib' if 'map_misc' in raw['id'] else 'Queko' if 'map_queko' in raw['id'] else ''
        instance = raw['name']
        category = 'synthetic'
    else:
        instance, display_name = raw['name'].split(': ')
        category = 'application'
 
    python_version = '.'.join(raw['python_version'].split('.')[:2])
    hw_descr = raw['hardware_description']
    metrics = list(raw['stats']['quality'].keys())
    tool = raw['tool']
    tool_version = raw['tool_version']
    algorithm = raw['algorithm']

    if tool == 'qiskit' and tool_version > NEWEST_QISKIT_VERSION:
        NEWEST_QISKIT_VERSION = tool_version
    
    results = { 'compile_time': raw['stats']['timings'] }
    for metric in metrics:
        results[metric] = raw['stats']['quality'][metric]

    benchmark_data[display_name][python_version][tool][tool_version][algorithm][hw_descr][instance] = results

# Build and export plots

output = {}

for benchmark_name in benchmark_data:
    # overview
    overview_fig = plt.Figure(figsize=(24,8))
    overview_fig.set_tight_layout(True)
    overview_quality_axis = overview_fig.add_subplot(121)
    overview_time_axis = overview_fig.add_subplot(122)

    if 'Queko' in benchmark_name or 'Revlib' in benchmark_name:
        ref_alg = 'sabre/sabre'
    else:
        ref_alg = 'opt_level = 1'
    from statistics import median
    reference_quality = benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION]['qiskit'][NEWEST_QISKIT_VERSION][ref_alg]

    all_tools_vers_algs = [(tool, ver, alg) for tool in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION]
                              for ver in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool]
                              for alg in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool][ver]]

    data = [ [val / median(reference_quality[hw][inst]['depth'])
              for hw in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool][ver][alg]
              for inst in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool][ver][alg][hw]
              if 'depth' in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool][ver][alg][hw][inst]
              for val in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool][ver][alg][hw][inst]['depth']
              if reference_quality[hw][inst]['depth'] # Dangling workers means we're missing some Qiskit data
              ]
             for (tool, ver, alg) in all_tools_vers_algs]

    #print(data)
    overview_quality_axis.violinplot(data, showmedians=True)

    overview_quality_axis.set_xticks([y + 1 for y in range(len(data))],
                                     labels=['\n'.join(vals) for vals in all_tools_vers_algs],
                                     )
    overview_quality_axis.set_ylabel(f'Output depth ratio relative to Qiskit {NEWEST_QISKIT_VERSION}')

    
    from statistics import median
    reference_quality = benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION]['qiskit'][NEWEST_QISKIT_VERSION][ref_alg]

    data = [ [np.log10(val / median(reference_quality[hw][inst]['compile_time']))
              for hw in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool][ver][alg]
              for inst in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool][ver][alg][hw]
              if 'compile_time' in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool][ver][alg][hw][inst]
              for val in benchmark_data[benchmark_name][OVERVIEW_PYTHON_VERSION][tool][ver][alg][hw][inst]['compile_time']
              if reference_quality[hw][inst]['compile_time']  # Dangling workers means we're missing some Qiskit data
              ]
             for (tool, ver, alg) in all_tools_vers_algs]

    overview_time_axis.violinplot(data)
    overview_time_axis.set_xticks([y + 1 for y in range(len(data))],
                                     labels=['\n'.join(vals) for vals in all_tools_vers_algs],
                                     )
    overview_time_axis.set_ylabel(f'Compile time ratio relative to Qiskit {NEWEST_QISKIT_VERSION}')

    overview_time_axis.yaxis.set_major_formatter(mticker.StrMethodFormatter("$10^{{{x:.0f}}}$"))
    ymin, ymax = overview_time_axis.get_ylim()
    tick_range = np.arange(np.floor(ymin), ymax)
    overview_time_axis.yaxis.set_ticks(tick_range)
    overview_time_axis.yaxis.set_ticks([np.log10(x) for p in tick_range for x in np.linspace(10 ** p, 10 ** (p + 1), 10)], minor=True)

    
    overview_fig.suptitle(benchmark_name + ' Overview')
    overview_fig.savefig(benchmark_name + '_overview.png')
    plt.close(overview_fig)

    # full data
    full_data_plot_paths = []

    for python_version in benchmark_data[benchmark_name]:
        for tool in benchmark_data[benchmark_name][python_version]:
            hw_descrs = sorted(list(list(benchmark_data[benchmark_name][python_version][tool].values())[0].values())[0].keys())

            for hardware_description in hw_descrs:
                metrics = list(reversed(sorted(list(list(list(benchmark_data[benchmark_name][python_version][tool].values())[0].values())[0][hardware_description].values())[0])))

                full_data_fig, metric_axs = plt.subplots(1, len(metrics), figsize=(24,8))
                if len(metrics) == 1:
                    metric_axs = [metric_axs]
                full_data_fig.set_tight_layout(True)

                all_vers_algs_insts = [(ver, alg, inst)
                                             #for tool in benchmark_data[benchmark_name][python_version]
                                             for ver in benchmark_data[benchmark_name][python_version][tool]
                                             for alg in benchmark_data[benchmark_name][python_version][tool][ver]
                                             for inst in benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description]]

                try:
                    all_vers_algs_insts.sort(key=lambda elt: (elt[0], elt[1], int(elt[2])))
                except:
                    all_vers_algs_insts.sort(key=lambda elt: (elt[0], elt[1], str(elt[2])))

                for metric, metric_ax in zip(metrics, metric_axs):
                    # data = [ [val
                    #          for inst in benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description]
                    #          for val in benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description][inst][metric]]
                    #          for (ver, alg, inst) in all_vers_algs_insts]
                    data = [ benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description][inst][metric]
                             for (ver, alg, inst) in all_vers_algs_insts
                             if metric in benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description][inst]
                             and benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description][inst][metric]
                            ]

                    cat = [(ver, alg, inst)
                           for (ver, alg, inst) in all_vers_algs_insts
                           if metric in benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description][inst]
                           and benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description][inst][metric]]

                    last_ver = None
                    last_alg = None
                    positions = []
                    tick_labels = []
                    pos_count = 0
                    for ver, alg, inst in cat:
                        if last_ver is None or ver != last_ver:
                            last_ver = ver
                            pos_count += 1
                            tick_labels.append(ver)

                        if last_alg is None or alg != last_alg:
                            last_alg = alg
                            pos_count += 1
                            tick_labels.append('\n' + alg)

                        positions.append(pos_count)
                        tick_labels.append('\n\n' + inst)
                        pos_count += 1                            

                    if data:
                        metric_ax.violinplot(data, positions)

                        # metric_ax.set_xticks([y + 1 for y in range(len(data))],
                        #                      labels=['\n'.join(vals) for vals in [(ver, alg, inst) for (ver, alg, inst) in all_vers_algs_insts if metric in benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description][inst] and benchmark_data[benchmark_name][python_version][tool][ver][alg][hardware_description][inst][metric]]],
                        #                              )
                        metric_ax.set_xticks(list(range(pos_count)), labels=tick_labels)
                        for xtl, tick_label in zip(metric_ax.get_xticklabels(), tick_labels):
                            if tick_label.startswith('\n\n'):
                                xtl.set_va('top')
                                xtl.set_ha('right')
                                xtl.set_text(tick_label[2:])
                                xtl.transform = metric_ax.transAxes
                                xtl.set_rotation('vertical')
                                xtl.set_y('-0.05')

                        metric_ax.set_ylabel(metric)

                full_data_fig.suptitle(f'{tool} for {hardware_description} Full data (Python {python_version})')
                plot_file_name = f"{benchmark_name}_{python_version}_{tool}_{hardware_description}.png"
                full_data_fig.savefig(plot_file_name)
                full_data_plot_paths.append(plot_file_name)
                plt.close(full_data_fig)
    
    # comparitive
    comparitive_plot_paths = []

    hw_descrs = list(sorted(list(list(list(list(benchmark_data[benchmark_name].values())[0].values())[0].values())[0].values())[0].keys()))
    metrics = list(reversed(sorted(list(list(list(list(list(list(benchmark_data[benchmark_name].values())[0].values())[0].values())[0].values())[0].values())[0].values())[0].keys())))


    for hardware_description in hw_descrs:
        
        for metric in metrics:
            all_pyver_tool_vers_algs = [(python_version, tool, ver, alg,)
                                        for python_version in benchmark_data[benchmark_name]
                                        for tool in benchmark_data[benchmark_name][python_version]
                                        for ver in benchmark_data[benchmark_name][python_version][tool]
                                        for alg in benchmark_data[benchmark_name][python_version][tool][ver]]

            comparitive_fig, comparitive_axs = plt.subplots(
                len(all_pyver_tool_vers_algs),
                len(all_pyver_tool_vers_algs),
                # sharex=True,  # Turning this on breaks gridlines
                # sharey=True,
                figsize=(16,16))
            comparitive_fig.set_tight_layout(True)
            comparitive_axs = comparitive_axs.flatten()
        

            ax_idx = -1
            for top_idx, top in enumerate(all_pyver_tool_vers_algs):
                for side_idx, side in enumerate(all_pyver_tool_vers_algs):
                    ax_idx += 1
                    ax = comparitive_axs[ax_idx]

                    if side_idx == 0:
                        ax.set_ylabel('\n'.join(top))

                    if top_idx == len(all_pyver_tool_vers_algs)-1:
                        ax.set_xlabel('\n'.join(side))

                    if top_idx == side_idx:
                        ax.set_xticks([])
                        ax.set_yticks([])
                        ax.set_facecolor('white')
                        continue

                    from statistics import median

                    xdata = [median(inst_vals[metric])
                             for inst_name, inst_vals in 
                             benchmark_data[benchmark_name][side[0]][side[1]][side[2]][side[3]][hardware_description].items()
                             if inst_vals[metric] and benchmark_data[benchmark_name][top[0]][top[1]][top[2]][top[3]][hardware_description][inst_name][metric]
                             ]
                    ydata = [median(inst_vals[metric])
                             for inst_name, inst_vals in 
                             benchmark_data[benchmark_name][top[0]][top[1]][top[2]][top[3]][hardware_description].items()
                             if inst_vals[metric] and benchmark_data[benchmark_name][side[0]][side[1]][side[2]][side[3]][hardware_description][inst_name][metric]]

                    ax.scatter(
                        xdata,
                        ydata,
                        s=16,
                        facecolors='none',
                        edgecolors='black',
                        alpha=0.8
                    )
                    if xdata and ydata:
                        min_pt = min(min(xdata), min(ydata))
                        max_pt = max(max(xdata), max(ydata))
                        ax.plot([min_pt, max_pt], [min_pt, max_pt], 'red', alpha=0.2)

                        ax.set_xscale('log')
                        ax.set_yscale('log')

            comparitive_fig.suptitle(f'{metric} comparitive on {hardware_description}')
            comparitive_fig_name = f"{benchmark_name}_{hardware_description}_{metric}_comparitive.png"
            comparitive_fig.savefig(comparitive_fig_name)
            comparitive_plot_paths.append(comparitive_fig_name)
            plt.close(comparitive_fig)

    output[benchmark_name] = [
        benchmark_name + '_overview.png',
        full_data_plot_paths,
        comparitive_plot_paths,
    ]

# Build and export HTML
html = "<html>\n  <body>\n"

for benchmark in output:
    html += f"    <h1>{benchmark}</h1>\n"
    html += f"      <img src=\"{output[benchmark][0]}\">\n"
    html += f"      <h2>Full Data</h2>\n"
    for full_data_path in output[benchmark][1]:
        html += f"      <div>\n"
        html += f"        <a href=\"#\" onClick=\"this.nextSibling.nextSibling.style.display = (this.nextSibling.nextSibling.style.display === 'none') ? 'block' : 'none'; return false;\">{full_data_path}</a>\n"
        html += f"        <img src=\"{full_data_path}\" style=\"display: none\">\n"
        html += f"      </div>\n"
    html += f"      <h2>Comparitive</h2>\n"
    for comparitive_path in output[benchmark][2]:
        html += f"      <div>\n"
        html += f"        <a href=\"#\" onClick=\"this.nextSibling.nextSibling.style.display = (this.nextSibling.nextSibling.style.display === 'none') ? 'block' : 'none'; return false;\">{comparitive_path}</a>\n"
        html += f"        <img src=\"{comparitive_path}\" style=\"display: none\">\n"
        html += f"      </div>\n"

        
html += "  </body>\n</html>"

with open('out.html', 'w') as f:
    f.write(html)
