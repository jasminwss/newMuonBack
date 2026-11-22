# Muons of the 2026 sample, propagated with cuda_muons to 50 cm before the end of the muon shield, then FairShip sim
# (frozen try_2026_v2 geometry, full SBT) by M. Smith, from A. Magnan (11.11.2026). Sim only, no reco.
FAIRSHIP=/afs/cern.ch/work/j/jaweiss/FairShip_latest
BRANCH=latest
INPUT_DIR=/eos/experiment/ship/simulation/cuda_muons/try_2026_v2_2026_muons_50cm_before_end_MS_261111
# 4 geo files for 65 sim files, not paired by name; the geometry is frozen (Tr1_1 at z = 8422 cm)
GEO=$INPUT_DIR/geo_3bf153b0-cc48-47e3-b139-803f8aff4986.root
EOS_BASE=/eos/user/j/jaweiss/newMuonBack/muons2026_full_SBT
# SUMW_TOT (sum of the muon weights of the full 2026 sample = 1 spill) not known yet, ask A. Magnan; until then
# the plots stay "weighted", not per spill
#SUMW_TOT=
