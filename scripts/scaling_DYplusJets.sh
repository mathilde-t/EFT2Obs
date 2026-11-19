#!/usr/bin/env bash
# Run get_scaling.py on every DYplusJets histogram of a merged yoda file.
#
# Usage: ./scripts/scaling_DYplusJets.sh <run folder> <config.json> [--nlo]
# config.json: the one the gridpack was built with, cards/<sample>/config.json
# Reads <run folder>/Rivet.yoda and writes <run folder>/scaling/scaling_<histogram>.{json,txt,log}
# --nlo: the weights come from NLO reweighting (passed on to get_scaling.py)
set -e

run_dir="${1:?Usage: $0 <run folder> <config.json> [--nlo]}"
config="${2:?Usage: $0 <run folder> <config.json> [--nlo]}"
nlo_flag="${3:-}"
out_dir="${run_dir}/scaling"
mkdir -p "${out_dir}"

# The histogram names: nominal weight only, without the RAW copies
hists=$(grep -E '^BEGIN YODA_HISTO1D_V2 /DYplusJets/[^[]*\[rw0000(_nlo)?\]$' "${run_dir}/Rivet.yoda" \
    | sed -E 's|.*/DYplusJets/([^[]*)\[rw0000(_nlo)?\]|\1|' || true)
if [ -z "${hists}" ]; then echo "ERROR: no DYplusJets histograms in ${run_dir}/Rivet.yoda"; exit 1; fi

for h in ${hists}; do
    echo "${h}"
    python scripts/get_scaling.py -c "${config}" -i "${run_dir}/Rivet.yoda" \
        --hist "/DYplusJets/${h}" --save json,txt -o "${out_dir}/scaling_${h}" ${nlo_flag} \
        > "${out_dir}/scaling_${h}.log" 2>&1 || echo "  FAILED, see ${out_dir}/scaling_${h}.log"
done
