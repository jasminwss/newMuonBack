# Neue Myon-Untergrund-Samples (cuda_muons)

Hier werden die von A. Magnan / M. Smith erzeugten Myon-Samples ausgewertet. Die Myonen wurden mit `cuda_muons` durch Target, Absorber und Muon Shield bis **50 cm vor das Ende des Muon Shields** propagiert. Ab dort folgt eine FairShip-Sim mit der eingefrorenen Geometrie `try_2026_v2` und vollem SBT. Es gibt **keine erzwungene DIS** und **keine Reco**, nur Sim-Dateien. Der Aufbau entspricht dem von `newMuonDIS`: `pipeline/`, eine `config.sh` pro Produktion und der Befehl `./prod`.

| Produktion | Eingabe | Sim-Dateien |
|---|---|---|
| `muons2018_full_SBT` | `/eos/experiment/ship/simulation/cuda_muons/try_2026_v2_2018_muons_50cm_before_end_MS_261111` | 596 |
| `muons2026_full_SBT` | `/eos/experiment/ship/simulation/cuda_muons/try_2026_v2_2026_muons_50cm_before_end_MS_261111` | 65 |

Jede Sim-Datei enthält 250 000 Events. In der getesteten 2018-Datei haben 387 davon Straw-Points und 28 191 SBT-Points. Die Myonen starten bei z ≈ 3164 cm. Die Geo-Dateien sind nicht per Namen den Sim-Dateien zugeordnet (30 bzw. 4 Stück). Die Geometrie ist eingefroren, deshalb nimmt `config.sh` eine feste Geo-Datei (`GEO`). Tr1 liegt hier bei z = 8422 cm, in der alten MuonBack-Geometrie bei 8407 cm. Das Skript liest den Wert aus der Geo-Datei. FairShip (`FairShip_latest`) dient nur als Umgebung zum Lesen von MCTrack usw.

## Befehle

```bash
cd /afs/cern.ch/work/j/jaweiss/private/newMuonBack
P=muons2018_full_SBT

./prod status                       # Überblick: x/596 Dateien je Modus, Jobs in der Queue, letzter Submit
./prod $P check
./prod $P cavern short --dry-run
./prod $P cavern short              # erst testen: 5 Dateien
./prod $P cavern full               # danach alle übrigen
./prod $P plot                      # hadd + Plots, läuft lokal

./prod $P cavern full --pdg         # mu+/mu- Modus, eigener Ordner
./prod $P plot --pdg
```

`cavern` submittet nur Dateien ohne Ausgabe. Um fehlgeschlagene Jobs zu wiederholen, rufst du `cavern full` einfach noch einmal auf. Pro Sim-Datei läuft ein Job, Flavour `longlunch`. Im Test dauerten 20 000 Events unter einer Minute, eine ganze Datei sollte also etwa 10 Minuten brauchen.

**Ausgabe** in `$EOS_BASE/<modus>/` (`<modus>` = `cavern` oder `cavern_pdg`):
- `hists/sim_<uuid>.root`: Histogramme pro Job
- `merged.root`: Summe aller Jobs (von `plot`)
- `plots/<produktion>_cavern_*.png`

**Ergebnis prüfen:** `./prod status` oder `grep -L SUCCESS $P/logs/cavern/cavern_<cluster>_*.out`. Keine Ausgabe heißt, alle Jobs waren erfolgreich.

## Skript `analysis/cavern_truth.py`

Truth-Version von `MuonBack/Inspection/cavern_spectrometer.py`. Die Klassifikation ist identisch: Cavern-Myon, Wand-Myon vor Tr1, Myon-Nachkommen aus der Wand.

- **Kategorien:** `all` (alle Cavern-Events) und `truth` (ein Myon aus der Wand hat Straw-MC-Points). `digi` und `reco` entfallen, weil es keine Reco gibt.
- **Normalmodus:** SBT-Zellmultiplizität und Edep pro Zelle bei 8 Schwellen, Wand-Vertex z-y und x-y, p und x-y am ersten Straw-Point in Station 1.
- **`--pdg`:** x des Wand-Vertex und θ_xz in Station 1, getrennt nach μ+ und μ− des Wand-Myons. Gelesen werden nur Events mit Straw-Points.
- **Gewichte:** `event_weight()` gibt das Myon-Gewicht `MCTrack[0].GetWeight()` (3.3 … 769) zurück, wie in MuonBack `cavern_spectrometer.py`; die Achsen heißen „weighted events/muons“. Laut A. Magnan ist das Gewicht pro Spill für das **ganze** Sample; weil nur ein Teil simuliert ist, skaliert `plot` mit `SUMW_TOT / ΣW_processed` (`SUMW_TOT` in `config.sh`, ΣW_processed summieren die Jobs im Histogramm `sumw_processed`). Dann heißen die Achsen „per spill“. Ohne `SUMW_TOT` (muons2026, noch unbekannt) bleibt es „weighted“.
- **Wand-z-y-Plot** geht bis z = 12 600 cm. Etwa 40 % der Wand-Wechselwirkungen liegen an der Rückwand (z > 12 052 cm). Im alten Skript (Achse bis 12 100) fehlten sie.

Lokal testen, ohne Condor:

```bash
export PATH=/cvmfs/ship-nightlies.cern.ch/pixi/0.72.0-rattlerfs-layers-d5a7568/bin:$PATH
pixi cvmfs /afs/cern.ch/work/j/jaweiss/FairShip_latest python analysis/cavern_truth.py \
    --sim <sim_X.root> --geo <geo.root> --out test.root --max-events 20000
pixi cvmfs /afs/cern.ch/work/j/jaweiss/FairShip_latest python analysis/cavern_truth.py --plot test.root --outdir test_plots --tag test_
```

## Wo liegt was

```
newMuonBack/
├── prod                      einziger Befehl, den du brauchst
├── analysis/cavern_truth.py  Truth-Cavern-Histogramme (fill pro Datei, plot nach hadd)
├── pipeline/cavern.sh/.sub   ein Job pro Sim-Datei
└── <produktion>/
    ├── config.sh             Eingabeordner, Geo-Datei, FairShip-Worktree, Ausgabeordner
    ├── submissions.log       welcher Cluster mit welchem Commit und welcher Skriptversion (md5) lief
    └── logs/<modus>/         Condor-Logs und Joblisten
```

Noch offen: Weitere Samples mit nur Stützstruktur und ganz ohne SBT werden gerade von M. Smith erzeugt. Dafür legst du einfach einen neuen Ordner mit `config.sh` an.
