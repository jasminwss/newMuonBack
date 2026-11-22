# Muons of the 2018 sample, propagated with cuda_muons to 50 cm before the end of the muon shield, then FairShip sim
# (frozen try_2026_v2 geometry, full SBT) by M. Smith, from A. Magnan (11.11.2026). Sim only, no reco.
FAIRSHIP=/afs/cern.ch/work/j/jaweiss/FairShip_latest
BRANCH=latest
INPUT_DIR=/eos/experiment/ship/simulation/cuda_muons/try_2026_v2_2018_muons_50cm_before_end_MS_261111
# 30 geo files for 596 sim files, not paired by name; the geometry is frozen (Tr1_1 at z = 8422 cm in all checked ones)
GEO=$INPUT_DIR/geo_0b051241-9013-4c3f-98dc-36ac379147f9.root
EOS_BASE=/eos/user/j/jaweiss/newMuonBack/muons2018_full_SBT
# sum of the muon weights of the FULL 2018 sample at 50 cm from the shield exit face = 1 spill (A. Magnan, 21.11.2026);
# plot scales by SUMW_TOT / (sum of weights of the processed events)
SUMW_TOT=3.4428233e+09
