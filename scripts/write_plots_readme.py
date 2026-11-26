#!/usr/bin/env python
"""Write README.md into the plot folder of a DYjets sample: what was generated, how, and what the
plots show. Everything is read from the files of the sample, nothing has to be passed by hand:
  cards/<sample>/                 process, model, beam energy, cuts, merging, operators
  <EOS>/<sample>/Rivet.yoda       events, cross sections (merged by step 4 of the driver)
  <EOS>/<sample>/Rivet_*.yoda     number of jobs
  jobs/<sample>/driver.log        dates of the steps, condor queue
  outputs/<sample>/ranking_*/     value of the coefficients in the rankings
  outputs/<sample>/plots/         the plots themselves

Usage, from the EFT2Obs folder:
  python scripts/write_plots_readme.py <sample> [--eos-dir DIR] [--out-dir DIR]
Called by step 5 of driver_run_DYjets_sample.sh after the plots.
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess

from plot_DYplusJets__readme import update_readme_date

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('sample', help='sample name: cards/<sample>, <eos-dir>/<sample>, outputs/<sample>')
parser.add_argument('--eos-dir', default='/eos/user/m/mwitt/EFT2Obs', help='parent of the run folder')
parser.add_argument('--out-dir', default='outputs', help='parent of outputs/<sample>')
args = parser.parse_args()

SAMPLE = args.sample
CARDS = os.path.join('cards', SAMPLE)
RUN = os.path.join(args.eos_dir, SAMPLE)
OUT = os.path.join(args.out_dir, SAMPLE)
PLOTS = os.path.join(OUT, 'plots')
JOB_DIR = os.path.join('jobs', SAMPLE)


def read(filename):
    with open(filename) as f:
        return f.read()


def run_card_value(name):
    """Value of '<value> = <name>' in run_card.dat, None if absent."""
    m = re.search(r'^\s*(\S+)\s*=\s*%s\b' % name, read(os.path.join(CARDS, 'run_card.dat')), re.M)
    return m.group(1) if m else None


def yoda_block(filename, path):
    """Lines of the YODA object with this path in a (large) yoda file, read line by line."""
    lines, inside = [], False
    with open(filename) as f:
        for line in f:
            if line.startswith('BEGIN ') and line.split()[-1] == path:
                inside = True
            elif inside:
                if line.startswith('END '):
                    return lines
                lines.append(line)
    return None


def data_rows(block):
    """Numeric rows of a YODA block, as lists of floats; labelled rows (Total, ...) are skipped."""
    rows = []
    for line in block or []:
        try:
            rows.append([float(x) for x in line.split()])
        except ValueError:
            pass
    return rows


def driver_step_date(pattern):
    """Date and time of the last driver.log step line that contains pattern."""
    log = os.path.join(JOB_DIR, 'driver.log')
    if not os.path.exists(log):
        return None
    found = None
    for line in read(log).splitlines():
        if line.startswith('=== ') and pattern in line:
            found = ' '.join(line.split()[1:3])
    return found


def requested_events():
    """(jobs, events per job) of the last submission, from its settings line in driver.log."""
    log = os.path.join(JOB_DIR, 'driver.log')
    if not os.path.exists(log):
        return None
    lines = read(log).splitlines()
    # the settings line printed just before the last '3. submitting' line
    last = None
    for i, line in enumerate(lines):
        if line.startswith('=== ') and '3. submitting' in line:
            last = i
    for line in reversed(lines[:last] if last is not None else []):
        m = re.search(r'settings: .*, (\d+) jobs x (\d+) events', line)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def git_state():
    """Commit of EFT2Obs and whether the files used here have uncommitted changes."""
    try:
        commit = subprocess.check_output(['git', 'log', '-1', '--format=%h (%cd)', '--date=short'],
                                         text=True).strip()
        files = ['scripts/plot_DYplusJets.py', 'scripts/rank_operators.py', 'scripts/driver_run_DYjets_sample.sh',
                 'RivetPlugins/DYplusJets.cc', CARDS]
        dirty = subprocess.check_output(['git', 'status', '--porcelain', '--'] + files, text=True).split('\n')
        dirty = sorted(set(line[3:].strip() for line in dirty if line.strip()))
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return 'unknown', []


# ---- Process and model, from the cards
proc_card = read(os.path.join(CARDS, 'proc_card.dat'))
model = re.search(r'^\s*import model\s+(\S+)', proc_card, re.M).group(1)
processes = [line.strip() for line in proc_card.splitlines()
             if re.match(r'\s*(generate|add process)\b', line)]
nlo = '[QCD]' in proc_card
order = 'NLO in QCD' if nlo else 'LO'
ebeam = float(run_card_value('ebeam1'))
sqrt_s = 2 * ebeam / 1000.

config = json.load(open(os.path.join(CARDS, 'config.json')))
operators = [p['name'] for p in config['parameters']]
reference_value = config.get('parameter_defaults', {}).get('val')
reweight_points = len(re.findall(r'^\s*launch', read(os.path.join(CARDS, 'reweight_card.dat')), re.M))

# Cuts and settings of the run card, as (name, meaning); only those present are listed
RUN_CARD_SETTINGS = [
    ('mmll', 'min m(l+l-) [GeV]'), ('mmllmax', 'max m(l+l-) [GeV]'), ('ptl', 'min pT(l) [GeV]'),
    ('etal', 'max abs. eta(l)'), ('drll', 'min dR(l,l)'), ('ptj', 'min pT(j) [GeV]'), ('etaj', 'max abs. eta(j)'),
    ('ickkw', 'merging (0 none, 1 MLM, 3 FxFx)'), ('xqcut', 'MLM xqcut [GeV]'),
    ('maxjetflavor', 'max jet flavour'), ('pdlabel', 'PDF'), ('lhaid', 'LHAPDF id'),
    ('dynamical_scale_choice', 'dynamical scale choice'),
]
run_settings = [(name, run_card_value(name), meaning) for name, meaning in RUN_CARD_SETTINGS
                if run_card_value(name) is not None]

# ---- Events and cross sections, from the yoda files on EOS
merged = os.path.join(RUN, 'Rivet.yoda')
n_jobs = len(glob.glob(os.path.join(RUN, 'Rivet_*.yoda')))
evtcount = data_rows(yoda_block(merged, '/RAW/_EVTCOUNT'))
n_events = int(evtcount[0][2]) if evtcount else None
xsec = data_rows(yoda_block(merged, '/RAW/_XSEC'))
xsec = xsec[0][0] if xsec else None
# ll_yields: bin 0 = all events with one Z candidate, bin 1 = with >= 1 jet (DYplusJets.cc). Cross
# sections from the SM of the scaling file, as in the plots: with MLM matching the nominal Rivet
# histograms are too high by 1/(matching efficiency), since they are divided by the number of events
# after the matching. Event counts from the nominal histogram.
yields = data_rows(yoda_block(merged, '/DYplusJets/ll_yields'))
yields_file = os.path.join(RUN, 'scaling', 'scaling_ll_yields.json')
yields_sm = json.load(open(yields_file))['sm_vals'] if os.path.exists(yields_file) else None
merged_date = datetime.datetime.fromtimestamp(os.path.getmtime(merged)).strftime('%Y-%m-%d %H:%M')

# ---- Rankings and plots
c_value = None
rankings = glob.glob(os.path.join(OUT, 'ranking_rate', '*.txt'))
if rankings:
    m = re.search(r'c = ([0-9.eE+-]+),', read(rankings[0]).splitlines()[0])
    c_value = m.group(1) if m else None
pngs = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(PLOTS, '*.png')))
histograms = sorted(set(re.sub(r'_(lin|log)$', '', p) for p in pngs))
commit, dirty = git_state()

# ---- README
md = []
md.append('## %s: plots\n' % SAMPLE) # title one size smaller than #, sections in bold (web view)
md.append('Drell-Yan + jets with SMEFT reweighting, %s, sqrt(s) = %g TeV, model `%s`.' % (order, sqrt_s, model))
md.append('Written %s by `scripts/write_plots_readme.py`.\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))

md.append('**Generation**\n')
md.append('MadGraph5_aMC@NLO process (`cards/%s/proc_card.dat`):\n' % SAMPLE)
md.append('```')
md += processes
md.append('```\n')
md.append('| Setting | Value | Meaning |')
md.append('|---|---|---|')
md.append('| ebeam1, ebeam2 | %g GeV | beam energy |' % ebeam)
for name, value, meaning in run_settings:
    md.append('| %s | %s | %s |' % (name, value, meaning))
md.append('')
md.append('Parton shower and hadronisation: Pythia 8 (`cards/%s/pythia8_card.dat`).' % SAMPLE)
md.append('Rivet routine: `DYplusJets` (`RivetPlugins/DYplusJets.cc`).\n')

md.append('**Events**\n')
md.append('| Quantity | Value |')
md.append('|---|---|')
requested = requested_events()
if requested:
    md.append('| requested | %d jobs x %d events = %d events |' % (requested[0], requested[1],
                                                              requested[0] * requested[1]))
md.append('| condor jobs (yoda files) | %d |' % n_jobs)
if n_events is not None:
    md.append('| events after the shower%s | %d |' % (' and the MLM matching' if run_card_value('ickkw') == '1'
                                                     else '', n_events))
    if n_jobs:
        md.append('| events per job | %d |' % round(n_events / float(n_jobs)))
    if requested and run_card_value('ickkw') == '1':
        md.append('| MLM matching efficiency | %.1f%% |' % (100. * n_events / (requested[0] * requested[1])))
if xsec is not None:
    md.append('| generator cross section%s | %.4g pb |' % (' after matching' if run_card_value('ickkw') == '1' else '',
                                                     xsec))
if len(yields) >= 2 and yields_sm:
    md.append('| SM, one Z candidate (Rivet selection) | %.4g pb (%d events) |' % (yields_sm[0], yields[0][6]))
    md.append('| SM, one Z candidate and >= 1 jet | %.4g pb (%d events) |' % (yields_sm[1], yields[1][6]))
for label, pattern in [('jobs submitted', '3. submitting'), ('step 4 started', '4. waiting')]:
    date = driver_step_date(pattern)
    if date:
        md.append('| %s | %s |' % (label, date))
md.append('| merged Rivet.yoda written | %s |' % merged_date)
md.append('')
md.append('Run folder: `%s` (yoda files, `scaling/`).\n' % RUN)

md.append('**SMEFT operators**\n')
md.append('%d operators enter this process (`cards/%s/config.json`), with %d reweighting points '
          '(%d weights per event with the nominal one), reference value %s.' %
          (len(operators), SAMPLE, reweight_points, reweight_points + 1, reference_value))
md.append('Coefficients in units of TeV^-2 (Lambda = 1 TeV).\n')
md.append(' '.join('`%s`' % o for o in operators) + '\n')

md.append('**Plots**\n')
md.append('Per histogram: the SM, the 3 leading operators by rate (solid) and the 3 leading by shape '
          '(dashed), each alone at c = %s, from `%s/ranking_rate/` and `%s/ranking_shape/`.' %
          (c_value, OUT, OUT))
md.append('An operator that leads in both rankings is drawn once, among the rate operators.')
md.append('Bands: statistical uncertainty of the EFT terms. Lower panel: ratio to the SM.')
md.append('The rankings belong to the histogram: plots of one histogram in several x ranges '
          '(`_full`, `_short`) show the same operators.\n')
md.append('File names: `<selection>_<channel>_<variable>[_<x range>]_<lin|log>.<png|pdf>`, '
          'with channel `ll` (ee + mumu), `ee`, or `mm`; `lin`/`log` is the y axis.')
md.append('%d plots of %d histograms, each as png and pdf.\n' % (len(pngs), len(histograms)))

md.append('**Code**\n')
md.append('EFT2Obs commit %s.' % commit)
if dirty:
    md.append('Uncommitted changes at the time of writing in: ' + ', '.join('`%s`' % d for d in dirty) + '.')
md.append('')

with open(os.path.join(PLOTS, 'README.md'), 'w') as f:
    f.write('\n'.join(md))
# Date of the plots (newest plot file), next to the date this README was written
update_readme_date(PLOTS)
print('written %s' % os.path.join(PLOTS, 'README.md'))
