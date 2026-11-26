# coding: utf-8

"""
Write the date of the plots into the README.md of a plot folder, so it always matches the plots next to it.
Used by plot_DYplusJets.py, plot_DYplusJets_SMsampleRatios.py, and write_plots_readme.py.
The date is the time of the newest .png/.pdf in the folder: it stays right after copying with rsync -a.
"""

import datetime
import glob
import os

date_line_start = 'Plots last updated:'


def update_readme_date(plot_dir):
    """Replace the line 'Plots last updated: ...' in plot_dir/README.md, or add it below the title (first line).
    Without a README, write one with only the date line."""
    # Date of the newest plot file, nothing to do without plots
    plot_files = glob.glob(os.path.join(plot_dir, '*.png')) + glob.glob(os.path.join(plot_dir, '*.pdf'))
    if not plot_files:
        return
    newest_time = max(os.path.getmtime(the_file) for the_file in plot_files)
    date_line = '%s %s' % (date_line_start, datetime.datetime.fromtimestamp(newest_time).strftime('%Y-%m-%d %H:%M'))

    # Read the README if there is one, else start from an empty one
    readme_path = os.path.join(plot_dir, 'README.md')
    lines = open(readme_path).read().splitlines() if os.path.exists(readme_path) else []

    # Replace the old date line, or add it: below the title, or alone in a new README
    date_idx = [line_idx for line_idx, the_line in enumerate(lines) if the_line.startswith(date_line_start)]
    if date_idx:
        lines[date_idx[0]] = date_line
    elif lines:
        lines[1:1] = ['', date_line]
    else:
        lines = [date_line]
    with open(readme_path, 'w') as readme_file:
        readme_file.write('\n'.join(lines) + '\n')
