#!/bin/bash
set -eo pipefail

# Truth cavern histograms (analysis/cavern_truth.py) of one sim file.
# Arguments (see cavern.sub, filled in by ../prod via the job list):
#   $1 = FAIRSHIP  FairShip worktree, only used as environment (pixi cvmfs)
#   $2 = SCRIPT    analysis/cavern_truth.py
#   $3 = SIM       sim_<uuid>.root
#   $4 = GEO       geo file of the sample (frozen geometry, the same for all sim files)
#   $5 = OUT       output ROOT file with the histograms
#   $6 = MODE_OPT  empty or --pdg
# If OUT already exists the job does nothing, so resubmitting only redoes what is missing.

FAIRSHIP=$1
SCRIPT=$2
SIM=$3
GEO=$4
OUT=$5
MODE_OPT=${6:-}

if [ -f "$OUT" ]; then
    echo "SUCCESS: nothing to do, $OUT exists."
    exit 0
fi
[ -f "$SIM" ] || { echo "ERROR: sim file missing: $SIM"; exit 1; }
[ -f "$GEO" ] || { echo "ERROR: geo file missing: $GEO"; exit 1; }

export QT_QPA_PLATFORM=offscreen
export PATH=/cvmfs/ship-nightlies.cern.ch/pixi/0.72.0-rattlerfs-layers-d5a7568/bin:$PATH
echo "Using FAIRSHIP=$FAIRSHIP (pixi cvmfs), branch $(git -C "$FAIRSHIP" branch --show-current), commit $(git -C "$FAIRSHIP" rev-parse --short HEAD)"
echo "Input: $SIM  mode: ${MODE_OPT:-normal}"

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

# local copies, the input folder is read through EOS fuse otherwise
cp "$SIM" sim.root
cp "$GEO" geo.root

pixi cvmfs "$FAIRSHIP" python "$SCRIPT" --sim sim.root --geo geo.root --out hists.root $MODE_OPT

[ -s hists.root ] || { echo "ERROR: no histogram file produced"; exit 1; }
mkdir -p "$(dirname "$OUT")"
# copy under a temporary name first, so an interrupted copy is never counted as done
cp hists.root "$OUT.part"
mv "$OUT.part" "$OUT"
echo "SUCCESS: $OUT"
