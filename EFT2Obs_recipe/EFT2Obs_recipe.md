# EFT2Obs recipe: what to edit and what to rerun

Example process: `DYjets` (cards in `cards/DYjets/`, Rivet routine `DYplusJets`).
Status: 2026-11-05.
Replace `DYjets` with your process name everywhere if you make a new one.

Rule of thumb: **every step depends on the ones above it.** If you change
something, rerun its step and *everything below it*.

---

## 0. Initialise the framework

### 0a. Install (once per clone)

```bash
. /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh
git clone https://github.com/ajgilbert/EFT2Obs.git ~/EFT2Obs
cd ~/EFT2Obs
source env.sh

./scripts/setup_mg5.sh               # LHAPDF, MadGraph, Pythia8 + EFT2Obs patches
./scripts/setup_rivet.sh             # Rivet, YODA, HepMC, FastJet into local/
source env.sh                        # once more, to pick up local/rivetenv.sh
./scripts/setup_model_SMEFTsim3.sh   # all SMEFTsim variants into MG5_aMC_v2_9_16/models/
./scripts/setup_rivet_plugins.sh     # compiles RivetPlugins/*.cc
```

Check the install:
```bash
python3 --version                                # 3.11.9
python3 -c "import lhapdf, rivet"                # no error
ls MG5_aMC_v2_9_16/models/ | grep SMEFTsim       # UFO folders are there
```

- **Keep this order.** The models live inside the MadGraph folder, so `setup_model_*` needs
  `setup_mg5.sh` first, and `setup_process.sh` (step 2) needs the model.
- `setup_mg5.sh` always prints `ERROR: environment variable LHAPDF_CONFIG_PATH is not set`
  at the start. That line is misleading and can be ignored.
- `RivetPlugins/DYplusJets.plot` and the scripts `plot_DYplusJets.py` and `rank_operators.py` are not in
  git (status 2026-11-05): on a new clone, copy them over before steps 7 and 8.
- **These scripts are not meant to be rerun:** `setup_mg5.sh` stops if `lhapdf/` or
  `MG5_aMC_v2_9_16/` exists, and `setup_model_SMEFTsim3.sh` stops if the models exist.
  Changing the model, process or cards never needs a reinstall.

**Using condor:** the jobs only run `source env.sh`, so they need the LCG line in it, otherwise
they fail with `python: command not found`:
```bash
sed -i '1a source /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh' env.sh
```
Keep this as a local edit and don't commit it (it would break CMSSW users). It can get lost
(it did on 2026-10-29), so check with `grep -n LCG_106 env.sh` before submitting.

**Only if the MadGraph install is really broken:** this also deletes all models and process
folders; your `cards/` stay.
```bash
rm -rf MG5_aMC_v2_9_16 lhapdf HEPToolsInstallers
./scripts/setup_mg5.sh
./scripts/setup_model_SMEFTsim3.sh
./scripts/setup_process.sh DYjets
./scripts/make_gridpack.sh DYjets 0 4
```
Rivet (`local/`) is not affected and does not need reinstalling.

### 0b. Every new terminal (always)

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
| Fresh clone, nothing installed yet               | none                                                 | **0a**        |
| Other SMEFTsim flavour/scheme (already installed) | `import model` line in `cards/DYjets/proc_card.dat` | **2**         |
| New model that is not installed yet (UFO)        | install into `MG5_aMC_v2_9_16/models/` + `proc_card.dat` | **1**     |
| Process, final state, extra jets, `NP<=1`        | `cards/DYjets/proc_card.dat`                         | **2**         |
| LO ↔ NLO (`[QCD]`)                               | `proc_card.dat`, model, NLO scripts (see NLO box)    | **1/2**       |
| Which EFT operators / their values               | `cards/DYjets/config.json` (via `auto_detect_operators.py` or `make_config.py`) | **3** |
| Generation params: energy, PDF, cuts, scales     | `cards/DYjets/run_card.dat`                          | **4**         |
| Shower settings (Pythia8, CMS tune)              | `cards/DYjets/pythia8_card.dat`                      | **4**         |
| Rivet observables / cuts / binning               | `RivetPlugins/DYplusJets.cc`                         | **5**         |
| Number of events / seeds / jobs                  | command line only                                    | **6**         |
| Which histogram to parametrise / rebinning       | command line only                                    | **7**         |
| Plot axis titles / legends                       | `RivetPlugins/DYplusJets.plot`, `plot_DYplusJets.py` | **8**         |

---

## 1. Model (only when the model is not installed yet)

**Skip this step when switching between SMEFTsim variants** (`top`, `topU3l`, `U35`, ...): step 0a
installed all of them, so just edit `proc_card.dat` and go to step 2.

Other models: `./scripts/setup_model_SMEFTatNLO.sh` (NLO), `./scripts/setup_model_HEL.sh`,
or unpack any UFO by hand into `MG5_aMC_v2_9_16/models/`, then check:
```bash
ls MG5_aMC_v2_9_16/models/          # check the UFO folder is there
```
If you really need to reinstall SMEFTsim3, remove it first, otherwise the script stops at `mv`
and leaves its download behind in `models/`:
```bash
rm -rf MG5_aMC_v2_9_16/models/SMEFTsim* MG5_aMC_v2_9_16/models/v3.0.2.tar.gz
./scripts/setup_model_SMEFTsim3.sh
```

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
- **Current `cards/DYjets/proc_card.dat`:** only `generate p p > l+ l- NP<=1 @0` (the `+ j` line is
  commented out), so all jets come from the shower.
- With `+ j` (and `+ j j`) processes, the jets need MLM merging: `ickkw = 1` and `xqcut` in `run_card.dat`
  (step 4). `cards/ggF-HEL` is a working example.

Rerun (the script refuses if the MG process folder already exists):
```bash
rm -rf MG5_aMC_v2_9_16/DYjets
./scripts/setup_process.sh DYjets
```
- `run_card.dat` / `pythia8_card.dat` in `cards/DYjets/` are **not overwritten** if they exist.
  If the process changed a lot (e.g. added jets → need matching/merging settings),
  delete them first to get fresh MG defaults, then re-apply your edits:
  `rm cards/DYjets/{run,pythia8}_card.dat` before `setup_process.sh`.
  **A fresh `run_card.dat` has `use_syst = True` again: set it back to `False` (see step 4).**

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
  - **m_ℓℓ range:** `mmll`/`mmllmax` should match the routine's mass window, 25–2000 GeV
    (`MLL_MIN`/`MLL_MAX` in `DYplusJets.cc`). The current card and gridpack still have 50 and 150 GeV:
    set `25.0 = mmll` and `2000.0 = mmllmax` for the next gridpack. Few events land in the tail of one flat
    sample, so generating in m_ℓℓ slices may be needed.
- `cards/DYjets/pythia8_card.dat` – shower settings
  (CMS-like tune: append `resources/pythia8/cms_default_2018.dat`).

**Required in `run_card.dat`: `False = use_syst`.** MadGraph's default is `True`, which adds
PDF/scale weights to every event. EFT2Obs's weight corrector (`setup/WeightCorrector.h`) works out
the number of operators from the total number of weights, so the extra weights break it:
with 33 operators (596 weights + 144 systematics) it gets 37, and Pythia crashes on the first event.
With fewer operators it may not crash, but it can still mix these weights into the EFT terms.
```bash
grep -n use_syst cards/DYjets/run_card.dat      # must show False
```

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

## 5. Rivet routine (`RivetPlugins/DYplusJets.cc`)

Z(→ee, μμ) + jets, inclusive in the jets and vs the number of jets, with no jet tagging.

- File **must end in `.cc`** (the build only picks up `RivetPlugins/*.cc`).
- **Cuts:** the constants in the block `@name Fiducial selection: change the cuts here` at the end of the class.
- **Variables and binning:** the `edges` map in `init()` and the `values` map in `fillVariables()`; both
  need the same keys. Bin edges do not follow the cuts: check the first and last bins after changing a cut.
- **Per-channel histograms:** `FIT_VARIABLES` (ee and μμ copies) and `MLL_SLICES` (cos θ\*_CS in m_ℓℓ slices).
- Histogram names: `zj_<channel>_<variable>` (channel `ll`, `ee`, or `mm`), e.g. `zj_ll_pTll`,
  `zj_ee_cosThetaCS_mll2`, plus `ll_nJets` and `ll_yields`.

```bash
./scripts/setup_rivet_plugins.sh
rivet --list-analyses DYplusJets     # check it is found
```
"Ignoring duplicate plugin" warnings are harmless.

**Quick test after a change (seconds):** run only the nominal weight on saved events.
```bash
export RIVET_ANALYSIS_PATH=$PWD/RivetPlugins
rivet -a DYplusJets --skip-weights -n 1000 -o test.yoda \
    /eos/user/m/mwitt/EFT2Obs/DYplusJets_1k/hepmc/events_4242.hepmc.gz
```
Compiling is not testing: errors like double booking only show up when Rivet runs.

**No new gridpack needed.** If you saved HepMC files before (`--save-hepmc`), you can
rerun only Rivet on them (step 6, `--load-hepmc`), without regenerating events.

---

## 6. Generate events + run Rivet

Each job's yoda file is ~260 MB (every histogram once per weight), so write to EOS, not AFS:
```bash
E=/eos/user/m/mwitt/EFT2Obs/<run name>        # a new folder for each run
```

Quick test (one job):
```bash
python scripts/run_gridpack.py --gridpack gridpack_DYjets.tar.gz -s 1 -e 500 \
    -p DYplusJets -o $E --save-hepmc $E/hepmc
```

Rivet-only rerun after editing the routine (reuses `$E/hepmc/events_1.hepmc.gz`):
```bash
python scripts/run_gridpack.py --gridpack gridpack_DYjets.tar.gz -s 1 \
    -p DYplusJets -o $E --load-hepmc $E/hepmc
```

Many jobs (local, 4 in parallel):
```bash
python scripts/launch_jobs.py --gridpack gridpack_DYjets.tar.gz -j 4 -s 1 -e 500 \
    -p DYplusJets -o $E --job-mode interactive --parallel 4
```
On condor: replace the last two options by
`--job-mode condor --task-name dyplusjets --sub-opts '+JobFlavour = "workday"'`.
This needs the LCG line in `env.sh` (step 0a). `-e` is events **per job**.

- **Use a new `-o` folder for each gridpack/model.** `yodamerge` on `Rivet_*.yoda` would
  otherwise mix in results from the previous run.
- **Condor "DONE" does not mean it worked.** The job script's exit code only reflects the last job,
  so failed jobs can still show as done. Check before merging:
  ```bash
  ls $E/Rivet_*.yoda | wc -l                       # must equal the number of jobs
  grep -il traceback dyplusjets.<ClusterId>.*.err  # must print nothing
  ```
- **Long runs:** use condor. Reweighting makes one pass over all events per reweight point (595 points
  took ~10 s each with 10k events, ~1 s each with 500), and a plain shell job dies when you log out.
  2000 events took 26 min.

Clean up after a failed condor run:
```bash
condor_rm <ClusterId>
rm -f core.* dyplusjets.<ClusterId>.*
rm -rf $E                         # only if it holds nothing from an earlier good run
```

Useful flags: `--to-step lhe|shower|rivet`, `--save-lhe DIR`, `--load-lhe DIR`, `--no-cleanup`.
`HIGGSPRODMODE` is only needed for the Higgs STXS routines, not for `DYplusJets`.

---

## 7. Merge + extract EFT scaling functions

```bash
# merge, only with more than one job (one job: cp $E/Rivet_1.yoda $E/Rivet.yoda)
yodamerge -o $E/Rivet.yoda $E/Rivet_*.yoda

# all DYplusJets histograms at once; writes $E/scaling/scaling_<hist>.json/.txt/.log
./scripts/scaling_DYplusJets.sh $E

# or one histogram
python scripts/get_scaling.py -c cards/DYjets/config.json -i $E/Rivet.yoda \
    --hist /DYplusJets/zj_ee_cosThetaCS_mll2 --save json,txt -o $E/scaling/scaling_zj_ee_cosThetaCS_mll2

# which operators matter for one histogram, at c = 0.3
python scripts/rank_operators.py $E/scaling/scaling_zj_ll_pTll.json 0.3
```
- Without `-o`, `get_scaling.py` writes to the **current directory**, named after the
  histogram (`/DYplusJets/zj_ll_mll` → `DYplusJets_zj_ll_mll.json`, `.txt`).
- The per-bin coefficient tables (value, uncertainty, rel. uncertainty) are printed to the
  terminal; `scaling_DYplusJets.sh` saves them in `$E/scaling/scaling_<hist>.log`.
- Options: `--rebin 50,70,90,110,150`, `--filter-params chdd,chwb`, `--print-style perTerm`.
- Use the **same `config.json`** that was used to build the gridpack.
- Run it only on the histograms you fit; the others are plotted from their nominal (SM) histogram, which is
  already in `Rivet.yoda`.

---

## 8. Plots: axis titles and legends

There are two kinds of plots.

### a) Rivet histograms (`rivet-mkhtml`): axis titles via a `.plot` file

Axis titles, plot titles, log scale, and legend position come from
`RivetPlugins/DYplusJets.plot`. It is found automatically because `env.sh` sets
`RIVET_ANALYSIS_PATH=RivetPlugins`. A histogram gets the settings of every block whose regex matches its
name, so the title comes from the channel blocks and the axis labels from the variable blocks. LaTeX syntax:
```
# BEGIN PLOT /DYplusJets/zj_ee_.*
Title=$pp \to ee$ + $\geq$1 jet
# END PLOT

# BEGIN PLOT /DYplusJets/.*_mll
XLabel=$m_{\ell\ell}$ [GeV]
YLabel=$\mathrm{d}\sigma/\mathrm{d}m_{\ell\ell}$ [pb/GeV]
# END PLOT
```
Other useful keys: `XMin`, `XMax`, `YMin`, `YMax`, `LogX`, `LogY`, `Legend=0` (hide), `RatioPlot=0`.
Editing the `.plot` file needs **no** recompilation, just rerun `rivet-mkhtml`.
(Alternatively pass a file explicitly: `rivet-mkhtml ... -c myplots.plot`.)

Legend entries are set per input file with `file.yoda:Title=...`; you can also
compare several files:
```bash
rivet-mkhtml "$E/Rivet.yoda:Title=SM (2000 events)" --no-weights -o outputs/<run name>/rivet_plots
rivet-mkhtml run1/Rivet.yoda:"Title=13 TeV" run2/Rivet.yoda:"Title=13.6 TeV" -o compare-plots
```
- By default **every EFT weight** is drawn as a faint line; add `--no-weights` to
  show only the nominal (SM), `--errs` to show error bars.
- Output: `<-o dir>/index.html`, plus `<-o dir>/DYplusJets/<hist>.png/.pdf`. Count them: `rivet-mkhtml`
  returns 0 even when some plots fail.
- **Status 2026-11-05:** `DYplusJets.plot` still has the variable names of the 2 Nov routine (`absyll`,
  `mZj`, and `.*_cosThetaCS`, which does not match the `_mll0`…`_mll3` slices).

### b) EFT plots (`scripts/plot_DYplusJets.py`): SM vs chosen operator values

Uses the scaling `.json` files from step 7 (needs ROOT, which LCG provides). One plot per variable and
channel, linear and log, PNG + PDF, in the style of `makePlot.py`:
```bash
python scripts/plot_DYplusJets.py -i $E -c cards/DYjets/config.json -o outputs/<run name>/plots \
    --draw chj3=0.3:4 chwb=0.3:2 che11=0.3:6 "chj3=0.3,chwb=0.3:8" --channels ll ee mm --ratio 0.8,1.2
```
- `--draw PAR1=X1,PAR2=X2:COLOR`: one line + legend entry per argument (ROOT colour number: 2 red, 4 blue,
  6 magenta, 8 green, ...).
- `--ratio lo,hi`: y-range of the ratio panel; `--show-unc`: stat. uncertainty band
  on the hypotheses; `--variables`, `--channels` to choose plots.
- Legend labels: edit `resources/translate_root_DY.json` (e.g. `"chj1": "c_{Hq}^{(1)}"`).
- **Status 2026-11-05:** the `VARIABLES` list in the script still has the names of the 2 Nov routine
  (`absyll`, `mZj`, and `cosThetaCS` without slices), so it does not cover all current histograms.

A single histogram with the generic EFT2Obs script:
```bash
python scripts/makePlot.py --hist $E/scaling_zj_ll_mll.json -c cards/DYjets/config.json \
    --x-title "m_{ll} [GeV]" --title-left "pp #rightarrow l^{+}l^{-} + #geq1 jet" --title-right "SMEFTsim3" \
    --draw chj3=0.3:4 chwb=0.3:2 --translate resources/translate_root_DY.json --ratio 0.8,1.2 --logy --y-min 1E-6
```
Output: `<json name>.png` and `.pdf` next to the `.json`. The y-axis title ("a.u.") and the legend position
are hard-coded in `scripts/makePlot.py` (search for `TLegend` / `a.u.`).

### c) Which plot is which, and how to read them

| Plots        | Files                                                        | Made by          |
|--------------|--------------------------------------------------------------|------------------|
| Rivet plots  | `<-o dir>/DYplusJets/<hist>.png/.pdf` (overview `<-o dir>/index.html`) | `rivet-mkhtml` |
| EFT plots    | `outputs/<run name>/plots/*.png/.pdf`                         | `plot_DYplusJets.py` |

**Rivet plots** (`DYplusJets/`):
- Solid red line = nominal weight = **SM** (because `config.json` generates at `--def-gen 0.0`).
- Faint lines = all other weights in the yoda file. These are **not** EFT hypotheses: EFT2Obs
  transforms the weights before Rivet (see README, "weight transformation"), so each faint
  line is one **isolated term** of the parametrisation (a linear term of one operator, a
  quadratic term, or a cross term of two operators, each at the `config.json` value, e.g. 0.01).
  - That is why many are orders of magnitude below the SM, and negative terms (e.g.
    interference) are invisible on a log scale.
  - They are named by number (`/DYplusJets/zj_ll_mll[rw0100]`, ...), not by operator, and get
    no legend entry → you **cannot** tell which is which. Use them only as a quick check.
  - Use `--no-weights` for clean SM-only plots.

**EFT plots**: **use these to compare hypotheses.**
- Black = SM; every other line = the full prediction SM × (1 + linear + quadratic) for one
  hypothesis given with `--draw`, labelled in the legend.
- New hypotheses need **no new events**: just change `--draw`, e.g.
  `--draw chdd=0.05:4 "chu=0.01,chd=0.01:8"`.
- With `DYplusJets.cc` (fixed normalisation, 2 Nov run) the effects are at the percent level, e.g. chj3 = 0.3
  gives +4 % in `zj`.

---

## Where is the output?

| What                                   | Where                                                    |
|----------------------------------------|----------------------------------------------------------|
| Rivet histograms per job (seed X)      | `$E/Rivet_X.yoda` on EOS, e.g. `$E/Rivet_1.yoda`         |
| Merged histograms                      | `$E/Rivet.yoda` (from `yodamerge`)                       |
| Scaling functions                      | `$E/scaling/scaling_<hist>.json` / `.txt` (`scaling_DYplusJets.sh`) |
| Per-bin coefficient tables             | `$E/scaling/scaling_<hist>.log`                          |
| Rivet plots                            | `<-o dir>/index.html` (from `rivet-mkhtml`)              |
| EFT plots                              | `outputs/<run name>/plots/` (from `plot_DYplusJets.py`)  |
| Standalone reweighting module          | `rw_module_DYjets.tar.gz` (only with `make_gridpack.sh DYjets 1 ...`) |
| LHE / HepMC files                      | only if `--save-lhe DIR` / `--save-hepmc DIR` was given  |
| Job working dir                        | `/tmp/$USER/gridpack_run_X`, deleted at the end unless `--no-cleanup` |

---

## Sanity-check the results before production

Check a small test run first (e.g. 500 events) before submitting many jobs:

1. **Statistics.** Look at `numEntries` per bin in `scaling_<hist>.log`. Only events that
   pass the Rivet selection count (e.g. `DYplusJets` needs ≥ 1 jet for all `zj_` histograms, ~14 % of the
   Z events, and the `ee`/`mm` histograms get only one flavour each). Empty bins or relative uncertainties
   close to 1 → more events, or coarser binning with `--rebin`.
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
That test also ran with `use_syst = True` (step 4), which may be the cause or part of it, also
**not verified**. Don't use results from before the fix; recheck these terms in the first new run.
Those `DY_EE` results are also biased by the Rivet normalisation (`crossSection()/sumW()`), which
`DYplusJets.cc` fixes. Whether the negative terms are still there with
`DYplusJets` was not checked.

---

## Reweighting: where it happens and how to apply it to a sample

**It is already done in step 6.** `run_gridpack.py` runs MadGraph's reweighting
(`madevent reweight GridRun`, the slowest part): every event gets one weight per point in
`reweight_card.dat` (here 595 points for 33 operators). Pythia keeps the weights, Rivet
fills every histogram once per weight (→ large `Rivet.yoda`), and `get_scaling.py`
turns them into per-bin scaling functions.

### Option A: per bin, with the scaling functions (standard EFT2Obs use)

`scaling_<hist>.json` gives per bin:

    sigma_EFT / sigma_SM = 1 + sum_i A_i c_i + sum_ij B_ij c_i c_j

Multiply the **SM prediction** in each bin (any SM DY sample, e.g. official CMS DY MC, or
data-driven) by this factor, or use it as the signal model in a fit (e.g. Combine).
Condition: the SM sample uses the **same selection and binning** as `DYplusJets`.

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
| `python3.9` paths / import errors          | wrong shell env: open new terminal, step 0b only, no CMSSW           |
| `Process directory already exists`          | `rm -rf MG5_aMC_v2_9_16/<proc>` then `setup_process.sh`              |
| `setup_process.sh`: model not found         | model not installed (e.g. after a MadGraph reinstall): step 0a/1 first, then `rm -rf MG5_aMC_v2_9_16/<proc>` and rerun |
| `setup_model_SMEFTsim3.sh`: `mv: cannot move ... Directory not empty` | models are already installed, nothing to do; `rm -rf MG5_aMC_v2_9_16/models/SMEFTsim-3.0.2 MG5_aMC_v2_9_16/models/v3.0.2.tar.gz` |
| `setup_mg5.sh`: `mkdir: cannot create directory 'lhapdf'` or `Directory ... already exists` | already installed, a model change doesn't need this; `rm -rf LHAPDF-6.5.3` if it was left behind |
| Pythia `free(): invalid next size`, core dumps, Rivet `Could not read ... events_N.hepmc` | `use_syst = True`: set `False` in `run_card.dat`, new gridpack (step 4) |
| Condor: `python: command not found`         | LCG line missing from `env.sh` (step 0a)                             |
| Condor jobs "DONE" but no `Rivet_*.yoda`    | jobs failed, read `<task name>.<ClusterId>.*.err` (step 6)           |
| Rivet: `analysis not found`                | file not `*.cc`, or forgot `setup_rivet_plugins.sh`                 |
| Rivet: `Found double-booking of ...`        | a histogram is booked twice, e.g. a booking loop inside another loop (step 5) |
| Results look like old settings              | gridpack not rebuilt after editing cards (step 4)                    |
| `get_scaling.py` wrong number of weights    | `config.json` differs from the one used for the gridpack             |
| Can't find the scaling `.json`/`.txt`       | written to the current directory unless `-o` is given                |
| Negative `cX * cX` terms                    | reweighting problem, see "Sanity-check the results"                  |
| Most bins empty                             | too few events pass the Rivet selection → more events / `--rebin`    |
