# EFT2Obs recipe: what to edit and what to rerun

Example process: `DYjets` (cards in `cards/DYjets/`, Rivet routine `DY_EE`).
Replace `DYjets` with your process name everywhere if you make a new one.

Rule of thumb: **every step depends on the ones above it.** If you change
something, rerun its step and *everything below it*.

---

## 0. Every new terminal (always)

```bash
. /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh
cd ~/EFT2Obs
source env.sh
```

- Do **not** set up CMSSW in the same shell.
- Source `env.sh` only once per shell (it prepends to `PYTHONPATH`/`LD_LIBRARY_PATH`).
- Sanity check: `python3 --version` → `3.11.9`.

---

## Quick lookup: "I changed X → start at step N"

| What you want to change                          | File(s) to edit                                      | Start at step |
|--------------------------------------------------|------------------------------------------------------|---------------|
| Physics model (UFO, e.g. other SMEFTsim flavour) | install into `MG5_aMC_v2_9_16/models/` + `proc_card.dat` | **1**     |
| Process, final state, extra jets, `NP<=1`        | `cards/DYjets/proc_card.dat`                         | **2**         |
| LO ↔ NLO (`[QCD]`)                               | `proc_card.dat`, model, NLO scripts (see NLO box)    | **1/2**       |
| Which EFT operators / their values               | `cards/DYjets/config.json` (via `auto_detect_operators.py` or `make_config.py`) | **3** |
| Generation params: energy, PDF, cuts, scales     | `cards/DYjets/run_card.dat`                          | **4**         |
| Shower settings (Pythia8, CMS tune)              | `cards/DYjets/pythia8_card.dat`                      | **4**         |
| Rivet observables / cuts / binning               | `RivetPlugins/DY_EE.cc`                              | **5**         |
| Number of events / seeds / jobs                  | command line only                                    | **6**         |
| Which histogram to parametrise / rebinning       | command line only                                    | **7**         |
| Plot axis titles / legends                       | `RivetPlugins/DY_EE.plot`, `makePlot.py` options     | **8**         |

---

## 1. Model (only when changing the UFO model)

SMEFTsim3 (all flavour/scheme variants):
```bash
./scripts/setup_model_SMEFTsim3.sh
ls MG5_aMC_v2_9_16/models/          # check the UFO folder is there
```
Other models: `./scripts/setup_model_SMEFTatNLO.sh` (NLO), `./scripts/setup_model_HEL.sh`,
or unpack any UFO by hand into `MG5_aMC_v2_9_16/models/`.

Restrictions (e.g. `-massless`) are the `restrict_*.dat` files inside the UFO folder.

Then update the `import model ...` line in `proc_card.dat` → continue with **step 2**.

---

## 2. Process (`cards/DYjets/proc_card.dat`)

Edit, e.g.:
```
import model SMEFTsim_topU3l_MwScheme_UFO-massless

generate p p > l+ l- NP<=1 @0
add process p p > l+ l- j NP<=1 @1

output DYjets
```
- `output <name>` **must equal** the `cards/<name>` folder name.
- Keep `NP<=1` (at most one EFT vertex per diagram) → linear + quadratic terms.

Rerun (the script refuses if the MG process folder already exists):
```bash
rm -rf MG5_aMC_v2_9_16/DYjets
./scripts/setup_process.sh DYjets
```
- `run_card.dat` / `pythia8_card.dat` in `cards/DYjets/` are **not overwritten** if they exist.
  If the process changed a lot (e.g. added jets → need matching/merging settings),
  delete them first to get fresh MG defaults, then re-apply your edits:
  `rm cards/DYjets/{run,pythia8}_card.dat` before `setup_process.sh`.

→ continue with **step 3** (the `param_card` must be rebuilt from the new process).

---

## 3. EFT operators: config → param_card → reweight_card

### 3a. (Recommended) Find the relevant operators automatically

`scripts/auto_detect_operators.py` reads the MG process folder made in step 2 and lists
which parameters actually enter the process. It checks the couplings used (`coupl.inc`),
and for SMEFTsim v3 also the `NP...` coupling orders of the Feynman diagrams and the
**propagator corrections** (operators that change the Z/W/H/top widths via `dWZ`, ...).

```bash
# only print the list, don't write anything
python scripts/auto_detect_operators.py -p DYjets --noConfigJson

# write cards/DYjets/config.json + cards/DYjets/reweight_card.dat
python scripts/auto_detect_operators.py -p DYjets \
    --def-val 0.01 --def-sm 0.0 --def-gen 0.0

# then the param_card (auto_detect does NOT make it)
python scripts/make_param_card.py -p DYjets -c cards/DYjets/config.json \
    -o cards/DYjets/param_card.dat
```
- Run it from the `EFT2Obs` folder, after `setup_process.sh` (it needs `MG5_aMC_v2_9_16/DYjets`).
- It **overwrites** `config.json` and `reweight_card.dat`; it also prints the
  `make_config.py ... --pars SMEFT:...` command it used, so you can copy that into 3b.
- The `import model ...` line must be the **first line** of `proc_card.dat`.
- `-b SMEFT,SMEFTcpv` to also look at CP-odd operators; `--set-inactive chdd chwb` to keep
  operators in the config but switch them off; `--noReweightCard` to skip the reweight card.
- If it stops with an `AssertionError` (the two methods disagree), rerun with `--noValidation`.

### 3b. By hand

Look up block names / indices in `MG5_aMC_v2_9_16/DYjets/Cards/param_card.dat`.

```bash
python scripts/make_config.py -p DYjets -o cards/DYjets/config.json \
    --pars SMEFT:5,9,26,28,30,32,103,104,105,107,108,109,113,115,117,119,121 \
    --def-val 0.01 --def-sm 0.0 --def-gen 0.0

python scripts/make_param_card.py -p DYjets -c cards/DYjets/config.json \
    -o cards/DYjets/param_card.dat

python scripts/make_reweight_card.py cards/DYjets/config.json cards/DYjets/reweight_card.dat
```
- `--def-val`: value used in the reweighting points; `--def-gen`: value used for generation (0 = SM).
- Per-parameter overrides: edit `config.json`, e.g. `{"index": 5, "name": "chdd", "val": 0.1}`,
  then rerun only `make_param_card.py` and `make_reweight_card.py`.
- NLO: `make_reweight_card.py ... --prepend 'change mode NLO'`.

→ continue with **step 4**.

---

## 4. Generation / shower cards → gridpack

Edit as needed:
- `cards/DYjets/run_card.dat` – `ebeam1/2`, `pdlabel`/`lhaid`, cuts (`ptl`, `mmll`, `etal`, ...),
  scales, `nevents` (only for the gridpack pilot run).
- `cards/DYjets/pythia8_card.dat` – shower settings
  (CMS-like tune: append `resources/pythia8/cms_default_2018.dat`).

Build the gridpack (copies all cards from `cards/DYjets/` into MG each time):
```bash
./scripts/make_gridpack.sh DYjets 0 4
#                          ^      ^ ^-- number of cores
#                          |      +---- 1 = also export standalone rw_module_DYjets.tar.gz
#                          +----------- cards folder
```
Output: `gridpack_DYjets.tar.gz` (overwritten). A 4th argument adds a postfix,
e.g. `./scripts/make_gridpack.sh DYjets 0 4 _13p6TeV` → `gridpack_DYjets_13p6TeV.tar.gz`;
further arguments are passed to MG, e.g. `"set ebeam1 6800" "set ebeam2 6800"`.

> **Any change in steps 1–4 needs a new gridpack.** The model, process,
> param_card, reweight points and run_card are all frozen inside it.

→ continue with **step 6** (step 5 only if the Rivet routine also changed).

---

## 5. Rivet routine (`RivetPlugins/DY_EE.cc`)

- File **must end in `.cc`** (the build only picks up `RivetPlugins/*.cc`).
- Change cuts / observables / binning in `init()` and `analyze()`.

```bash
./scripts/setup_rivet_plugins.sh
rivet --list-analyses DY_EE          # check it is found
```
"Ignoring duplicate plugin" warnings are harmless.

**No new gridpack needed.** If you saved HepMC files before (`--save-hepmc`), you can
rerun only Rivet on them (step 6, `--load-hepmc`), without regenerating events.

---

## 6. Generate events + run Rivet

Quick test (one job):
```bash
python scripts/run_gridpack.py --gridpack gridpack_DYjets.tar.gz -s 1 -e 500 \
    -p DY_EE -o test-dy --save-hepmc hepmc-dy
```

Rivet-only rerun after editing the routine (reuses `hepmc-dy/events_1.hepmc.gz`):
```bash
python scripts/run_gridpack.py --gridpack gridpack_DYjets.tar.gz -s 1 \
    -p DY_EE -o test-dy --load-hepmc hepmc-dy
```

Many jobs (local, 4 in parallel):
```bash
python scripts/launch_jobs.py --gridpack gridpack_DYjets.tar.gz -j 4 -s 1 -e 500 \
    -p DY_EE -o test-dy --job-mode interactive --parallel 4
```
On condor: replace the last two options by
`--job-mode condor --task-name dy --sub-opts '+JobFlavour = "longlunch"'`.

Useful flags: `--to-step lhe|shower|rivet`, `--save-lhe DIR`, `--load-lhe DIR`, `--no-cleanup`.
`HIGGSPRODMODE` is only needed for the Higgs STXS routines, not for `DY_EE`.

---

## 7. Merge + extract EFT scaling functions

```bash
yodamerge -o test-dy/Rivet.yoda test-dy/Rivet_*.yoda

# all DY_EE histograms at once; -o puts the results next to the yoda files
for h in m_ee pT_ee y_ee cosThetaCS; do
  python scripts/get_scaling.py -c cards/DYjets/config.json -i test-dy/Rivet.yoda \
      --hist "/DY_EE/$h" --save json,txt -o test-dy/scaling_$h > test-dy/scaling_$h.log 2>&1
done

# plots of all histograms -> open test-dy/plots/index.html
rivet-mkhtml test-dy/Rivet.yoda -o test-dy/plots
```
- Without `-o`, `get_scaling.py` writes to the **current directory**, named after the
  histogram (`/DY_EE/m_ee` → `DY_EE_m_ee.json`, `DY_EE_m_ee.txt`).
- The per-bin coefficient tables (value, uncertainty, rel. uncertainty) are printed to the
  terminal; the loop above saves them in `test-dy/scaling_<hist>.log`.
- Options: `--rebin 50,70,90,110,150`, `--filter-params chdd,chwb`, `--print-style perTerm`.
- Use the **same `config.json`** that was used to build the gridpack.

---

## 8. Plots: axis titles and legends

There are two kinds of plots.

### a) Rivet histograms (`rivet-mkhtml`): axis titles via a `.plot` file

Axis titles, plot titles, log scale and legend position come from
`RivetPlugins/DY_EE.plot`. It is found automatically because `env.sh` sets
`RIVET_ANALYSIS_PATH=RivetPlugins`. One block per histogram, LaTeX syntax:
```
# BEGIN PLOT /DY_EE/m_ee
Title=Drell-Yan $pp \to e^+e^-$
XLabel=$m_{ee}$ [GeV]
YLabel=$\mathrm{d}\sigma/\mathrm{d}m_{ee}$ [pb/GeV]
LogY=1
# END PLOT

# BEGIN PLOT /DY_EE/.*          <- regex: applies to all DY_EE histograms
LegendXPos=0.60
LegendYPos=0.90
RatioPlotYLabel=EFT/SM
# END PLOT
```
Other useful keys: `XMin`, `XMax`, `YMin`, `YMax`, `LogX`, `Legend=0` (hide), `RatioPlot=0`.
Editing the `.plot` file needs **no** recompilation, just rerun `rivet-mkhtml`.
(Alternatively pass a file explicitly: `rivet-mkhtml ... -c myplots.plot`.)

Legend entries are set per input file with `file.yoda:Title=...`; you can also
compare several files:
```bash
rivet-mkhtml test-dy/Rivet.yoda:"Title=SM (MG5 LO)" -o test-dy/plots
rivet-mkhtml run1/Rivet.yoda:"Title=13 TeV" run2/Rivet.yoda:"Title=13.6 TeV" -o compare-plots
```
- By default **every EFT weight** is drawn as a faint line; add `--no-weights` to
  show only the nominal, `--errs` to show error bars.
- Output: `test-dy/plots/index.html`, plus `test-dy/plots/DY_EE/<hist>.png/.pdf`.

### b) EFT plots (`scripts/makePlot.py`): nominal vs chosen operator values

Uses the scaling `.json` from step 7 (needs ROOT, which LCG provides). The legend
is made automatically from `--draw`, the axis title comes from `--x-title`, and
operator names are converted to nice labels with `--translate` (ROOT LaTeX, `#` not `\`).
```bash
cd test-dy
python ../scripts/makePlot.py --hist scaling_pT_ee.json -c ../cards/DYjets/config.json \
    --x-title "p_{T}^{ee} [GeV]" --title-left "pp #rightarrow e^{+}e^{-}" --title-right "SMEFTsim3" \
    --draw chj1=0.01:4 chwb=0.01:2 "chdd=0.01,chwb=0.01:8" \
    --translate ../resources/translate_root_DY.json --ratio 0.5,1.5 --show-unc --logy --y-min 1E-6
cd ..
```
- `--draw PAR1=X1,PAR2=X2:COLOR`: one line + legend entry per argument (ROOT colour number: 2 red, 4 blue, 8 green, ...).
- `--ratio lo,hi`: y-range of the ratio panel; `--show-unc`: stat. uncertainty band; `--logy`, `--y-min`.
- Legend labels: edit `resources/translate_root_DY.json` (e.g. `"chj1": "c_{Hq}^{(1)}"`).
- The y-axis title ("a.u.") and legend position are hard-coded in `scripts/makePlot.py`
  (search for `TLegend` / `a.u.` there to change them).
- Output: `<json name>.png` and `.pdf` in the current folder, e.g. `test-dy/scaling_pT_ee.png`.

All four histograms at once:
```bash
cd test-dy
declare -A XT=([m_ee]="m_{ee} [GeV]" [pT_ee]="p_{T}^{ee} [GeV]" [y_ee]="y_{ee}" [cosThetaCS]="cos#theta^{*}_{CS}")
for h in m_ee pT_ee y_ee cosThetaCS; do
  python ../scripts/makePlot.py --hist scaling_$h.json -c ../cards/DYjets/config.json --x-title "${XT[$h]}" \
    --title-left "pp #rightarrow e^{+}e^{-}" --title-right "SMEFTsim3" --draw chj1=0.01:4 chwb=0.01:2 \
    --translate ../resources/translate_root_DY.json --ratio 0,3 --y-min 1E-6
done
cd ..
```

### c) Which plot is which, and how to read them

| Plots        | Files                                                        | Made by          |
|--------------|--------------------------------------------------------------|------------------|
| Rivet plots  | `test-dy/plots/DY_EE/<hist>.png/.pdf` (overview `test-dy/plots/index.html`) | `rivet-mkhtml` |
| EFT plots    | `test-dy/scaling_<hist>.png/.pdf`                            | `makePlot.py`    |

**Rivet plots** (`plots/DY_EE/`):
- Solid red line = nominal weight = **SM** (because `config.json` generates at `--def-gen 0.0`).
- Faint lines = all other weights in the yoda file. These are **not** EFT hypotheses: EFT2Obs
  transforms the weights before Rivet (see README, "weight transformation"), so each faint
  line is one **isolated term** of the parametrisation (a linear term of one operator, a
  quadratic term, or a cross term of two operators, each at the `config.json` value, e.g. 0.01).
  - That is why many are orders of magnitude below the SM, and negative terms (e.g.
    interference) are invisible on a log scale.
  - They are named by number (`/DY_EE/m_ee[100]`, `[101]`, ...), not by operator, and get
    no legend entry → you **cannot** tell which is which. Use them only as a quick check.
  - Use `--no-weights` for clean SM-only plots.

**EFT plots** (`scaling_<hist>.png`): **use these to compare hypotheses.**
- Black = SM; every other line = the full prediction SM × (1 + linear + quadratic) for one
  hypothesis given with `--draw`, labelled in the legend.
- New hypotheses need **no new events**: just change `--draw`, e.g.
  `--draw chdd=0.05:4 "chu=0.01,chd=0.01:8"`.
- Status 2026-10-26: the EFT lines are far too large (Z-peak / reweighting issue, see
  "Sanity-check the results"), so the current plots are a format check only.

---

## Where is the output?

| What                                   | Where                                                    |
|----------------------------------------|----------------------------------------------------------|
| Rivet histograms per job (seed X)      | `<-o dir>/Rivet_X.yoda`, e.g. `test-dy/Rivet_1.yoda`     |
| Merged histograms                      | `test-dy/Rivet.yoda` (from `yodamerge`)                  |
| Scaling functions                      | `test-dy/scaling_<hist>.json` / `.txt` (with `-o`)       |
| Per-bin coefficient tables             | terminal output / `test-dy/scaling_<hist>.log`           |
| Plots                                  | `test-dy/plots/index.html` (from `rivet-mkhtml`)         |
| EFT plots                              | `test-dy/scaling_<hist>.png/.pdf` (from `makePlot.py`)   |
| Standalone reweighting module          | `rw_module_DYjets.tar.gz` (only with `make_gridpack.sh DYjets 1 ...`) |
| LHE / HepMC files                      | only if `--save-lhe DIR` / `--save-hepmc DIR` was given  |
| Job working dir                        | `/tmp/$USER/gridpack_run_X`, deleted at the end unless `--no-cleanup` |

---

## Sanity-check the results before production

Check a small test run first (e.g. 500 events) before submitting many jobs:

1. **Statistics.** Look at `numEntries` per bin in `scaling_<hist>.log`. Only events that
   pass the Rivet selection count (e.g. `DY_EE` keeps only e+e-, while `p p > l+ l-` also
   makes mu+mu-). Empty bins or relative uncertainties close to 1 → more events, or coarser
   binning with `--rebin`.
2. **Quadratic terms must be ≥ 0.** A term `cX * cX` is a |amplitude|² and can never be
   negative. Large negative values with small uncertainties mean the reweighting is
   not working correctly, not just low statistics.
3. **Magnitudes.** Coefficients of order 10^4–10^5 per unit Wilson coefficient are
   unrealistic for Λ = 1 TeV.

Known issue in the first DYjets test (2026-10-26, 500 events): at the Z peak (90–92 GeV)
`chdd*chdd ≈ -47000`, `chu*chu ≈ -56000`. Suspected cause, **not yet verified**: reweighting
across the narrow Z resonance while the Z width in `param_card.dat` (`DECAY 23 2.4952`)
stays fixed when the operators change (SMEFTsim's propagator-correction settings). Fixing it
would mean changing the param_card / reweight setup → back to **step 3**, new gridpack.

---

## Reweighting: where it happens and how to apply it to a sample

**It is already done in step 6.** `run_gridpack.py` runs MadGraph's reweighting
(`madevent reweight GridRun`, the slowest part): every event gets one weight per point in
`reweight_card.dat` (here ~170 points for 17 operators). Pythia keeps the weights, Rivet
fills every histogram once per weight (→ large `Rivet.yoda`), and `get_scaling.py`
turns them into per-bin scaling functions.

### Option A: per bin, with the scaling functions (standard EFT2Obs use)

`scaling_<hist>.json` gives per bin:

    sigma_EFT / sigma_SM = 1 + sum_i A_i c_i + sum_ij B_ij c_i c_j

Multiply the **SM prediction** in each bin (any SM DY sample, e.g. official CMS DY MC, or
data-driven) by this factor, or use it as the signal model in a fit (e.g. Combine).
Condition: the SM sample uses the **same selection and binning** as `DY_EE`.

### Option B: per event, standalone reweighting of an existing sample

```bash
# 1. Build the gridpack with the standalone module export switched on (2nd argument = 1)
./scripts/make_gridpack.sh DYjets 1 4          # -> rw_module_DYjets.tar.gz
# 2. Pack module + config + one param_card per reweighting point
python scripts/make_standalone.py -p DYjets -o rw_DYjets -c cards/DYjets/config.json \
    --rw-module rw_module_DYjets.tar.gz
```
Then per event in Python (needs LHE-level partons: 4-momenta, PDG IDs, helicities, status, alpha_s):
```python
import sys; sys.path.insert(0, 'scripts')
from standalone_reweight import StandaloneReweight
rw = StandaloneReweight('rw_DYjets')
w  = rw.ComputeWeights(parts, pdgs, helicities, status, alphas, True)  # parts = [[E,px,py,pz], ...]
tw = rw.TransformWeights(w)
new_w = rw.CalculateWeight(tw, chdd=0.1, chwb=0.05)   # weight for any operator values
```
- **Which module?** Always one built from the *current* `proc_card` / `config.json`.
  (The old `rw_module_DYjets.tar.gz` from 2026-10-25 contains `+ j` subprocesses and
  does not match the current 0-jet setup; don't use it.)
- **Which sample?** Only events whose parton configuration exists in your MG process can
  be reweighted. Current `proc_card` = `p p > l+ l-` only. Official DY samples usually have
  0–4 extra jets → `ComputeWeights` prints an error for those events. To reweight such a
  sample, add the `+ j` processes in `proc_card.dat` (step 2) and use the same model /
  flavour scheme as the sample.
- Standalone reweighting does not work with NLO matrix elements.
- Options A and B use the same reweighting, so fix the Z-peak issue above first.

---

## NLO box (LO → NLO in QCD)

| Step | LO                         | NLO                                                  |
|------|----------------------------|------------------------------------------------------|
| 1    | e.g. SMEFTsim3             | NLO-capable model, e.g. `setup_model_SMEFTatNLO.sh`  |
| 2    | `setup_process.sh`         | `setup_process_NLO.sh`, process with `[QCD]`         |
| 3    | `make_reweight_card.py`    | add `--prepend 'change mode NLO'`                    |
| 4    | `pythia8_card.dat`         | `shower_card.dat`; in `run_card`: `parton_shower = PYTHIA8`, `req_acc = 0.001`, `store_rwgt_info = True`, `reweight_scale = True` |
| 4    | `make_gridpack.sh`         | `make_gridpack_NLO.sh`                               |
| 6/7  | –                          | add `--nlo` to `run_gridpack.py` and `get_scaling.py` |

---

## Troubleshooting

| Symptom                                     | Cause / fix                                                          |
|---------------------------------------------|----------------------------------------------------------------------|
| `python3.9` paths / import errors          | wrong shell env: open new terminal, step 0 only, no CMSSW            |
| `Process directory already exists`          | `rm -rf MG5_aMC_v2_9_16/<proc>` then `setup_process.sh`              |
| Rivet: `analysis not found`                | file not `*.cc`, or forgot `setup_rivet_plugins.sh`                 |
| Results look like old settings              | gridpack not rebuilt after editing cards (step 4)                    |
| `get_scaling.py` wrong number of weights    | `config.json` differs from the one used for the gridpack             |
| Can't find the scaling `.json`/`.txt`       | written to the current directory unless `-o` is given                |
| Negative `cX * cX` terms                    | reweighting problem, see "Sanity-check the results"                  |
| Most bins empty                             | too few events pass the Rivet selection → more events / `--rebin`    |
