# DFDI: deltoid fatty degeneration index (CT)

Measure deltoid quality and quantity on shoulder CT, following Rescigno et al. 2026
(Eur J Orthop Surg Traumatol 36:424): cross-sectional area (CSA) and mean HU on one axial slice
at the superior greater tuberosity, combined into the **DFDI**.

> DFDI = 0.50 × (−Z_HU) + 0.50 × (−Z_CSA). **Higher** = **more** degeneration.
> Z-scores are computed **within a cohort**, so a patient's DFDI always refers to a group.

Two ways to use it:

1. **Web app**: upload a CT, pick the slice, draw the deltoid, press *Calculate*.
2. **Command line**: you already have a CT NIfTI + a deltoid mask.

Full protocol (Portuguese): [`docs/protocolo_medicao_DFDI.md`](docs/protocolo_medicao_DFDI.md).
Work plan (Portuguese): [`docs/PLANO_DE_TRABALHO.md`](docs/PLANO_DE_TRABALHO.md).

## Setup (once)

```bash
cd "/Users/brunogobbato/Dropbox/Claude Workspace/Deltoid-Fatty-Infiltration"
python3 -m venv .venv                 # already exists; only if deleted
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .            # creates .venv/bin/dfdi
.venv/bin/pytest -q                   # synthetic phantoms, no patient data
```

## 1. Web app

**With Docker (recommended):**

```bash
docker compose up -d --build      # first build ~2 min; image ~0.5 GB
docker compose logs -f            # see the server log
docker compose down               # stop
```

Cases and `results.csv` stay in `./dados` on this computer (mounted at `/data` in the container).
The port is bound to `127.0.0.1` only. Versions are pinned in `requirements.lock`.
Run the tests inside the image: `docker run --rm dfdi:local sh -c "cp -r /app /tmp/t && cd /tmp/t && python -m pytest -q -p no:cacheprovider tests"`.

**On a server (online):** the app runs behind nginx (HTTPS + basic auth) with `docker-compose.vps.yml`
(container on `127.0.0.1:18090`, data in `/opt/dfdi/data`, dedicated uid 10001). Copy the code (no data) and rebuild:

```bash
rsync -az --delete --exclude .venv --exclude dados --exclude output --exclude saida --exclude docs --exclude '*.pdf' --exclude '*.nii*' --exclude __pycache__ --exclude .pytest_cache --exclude '*.egg-info' --exclude .claude --exclude data ./ "$DFDI_VPS:/opt/dfdi/"
```
```bash
ssh "$DFDI_VPS" 'cd /opt/dfdi && docker compose -f docker-compose.vps.yml up -d --build'
```

Server details and logins are kept outside the repository.

**Without Docker (development):**

```bash
.venv/bin/uvicorn app.server:app --port 8080
```

Open `http://localhost:8080`.

1. **Upload CT**: drop a `.zip` with DICOM (converted with dcm2niix, patient name removed) or a `.nii.gz`.
2. **Series**: the soft-tissue series with the most slices opens first.
3. **Window**: Muscle (W400/L50), Soft tissue, Bone, or type W/L. Right-drag also changes the window.
4. **View**: 3 planes or a single plane. Mouse wheel or the slider changes the axial slice. HU under the crosshair.
5. **Reorient**: *Shaft distal* and *Shaft proximal* (click the centre of the medullary canal on two axial levels,
   ≥ 2 cm apart, proximal just below the surgical neck); optional *Glenoid anterior/posterior rim* so the coronal plane
   is parallel to the scapula. *Reorient* creates a new series (marked ⟂) with the axial plane perpendicular to the shaft
   (same pixel size and slice thickness, 20 × 20 cm box). Draw on that series.
6. **Reference slice**: tick the article criteria (circumferentially corticated greater tuberosity, humeral head visible, no surgical neck). The choice is the surgeon's.
7. **Draw**: *Deltoid* (red) traces a closed outline that fills on release; *Exclude* (green) for hematoma, fluid or fragments; *Erase area*, *Undo*, *Clear*. One axial slice only. The live area is shown.
8. **Calculate**: CSA, HU mean, DFDI (article reference, approximate), fat %, flags and a QC image.
   *Download all results (CSV)* gives one row per measurement.

Data lives in `dados/` (ignored by git and Dropbox). Use `DFDI_DATA=/path` for another folder.

Without reorientation a tilted shaft inflates CSA by 1/cos(tilt) (25° → +10%); the page shows the estimate after the two shaft points.

## 2. Command line

### Inputs

| File | Required | Note |
|---|---|---|
| `ct.nii.gz` | yes | in HU. Convert with `dcm2niix -b y` and keep the `.json` next to it |
| `deltoid.nii.gz` | yes | **same grid** as the CT. Any value > 0 = deltoid (or choose with `--labels`) |
| `humerus.nii.gz` | no | only to reorient or suggest the slice (e.g. TotalSegmentator) |

The mask can be **a single slice** (the article ROI; that slice is used) or **3D** (whole deltoid; then give the reference slice).

### One case

```bash
# you know the reference slice (0-based, the K of IJK in 3D Slicer)
.venv/bin/dfdi measure --ct ct.nii.gz --mask deltoid.nii.gz --slice-index 112 --out output/pt01 --case-id pt01

# ask for a candidate slice (you confirm it on the figure)
.venv/bin/dfdi measure --ct ct.nii.gz --mask deltoid.nii.gz --humerus humerus.nii.gz \
    --auto-slice --out output/pt01 --case-id pt01

# tilted shaft: reorient perpendicular to the shaft (needs a 3D mask)
.venv/bin/dfdi measure --ct ct.nii.gz --mask deltoid.nii.gz --humerus humerus.nii.gz \
    --reorient --auto-slice --save-reoriented --out output/pt01 --case-id pt01
```

Outputs in `output/pt01/`: `pt01_metrics.json`, `pt01_metrics.csv`, `pt01_overlay.png`
(ROI red, fat yellow, excluded cyan, histogram — **always look at it**), and `pt01_slice_candidates.png` with `--auto-slice`.

A single case gets `dfdi_article_approx`, computed with the article's published mean/SD.
**Approximation only** (other scanner, other cohort). For your own reference: `--cohort-csv my_cohort.csv` (columns `hu_mean`, `csa_mm2`).

### Batch

```
cases/
  pt01/  ct.nii.gz  deltoid.nii.gz  [humerus.nii.gz]  [slice.txt]
  pt02/  ...
```

`slice.txt` holds only the confirmed slice index (e.g. `112`).

```bash
.venv/bin/dfdi batch --root cases --out output/batch
# or a spreadsheet: case_id,ct,mask[,humerus,slice_index,labels]
.venv/bin/dfdi batch --manifest cases.csv --out output/batch
```

Outputs in `output/batch/`: `results.csv` (one row per patient, with `dfdi_cohort` from the batch's own z-scores,
as in the article), `cohort_reference.json` (mean/SD used; reuse with `--cohort-csv output/batch/results.csv`), `figures/`.
A failing case does not stop the batch: it gets the `error` column.

### Useful options

| Option | Purpose |
|---|---|
| `--labels 1,2,3` | mask labels that are deltoid |
| `--exclude-label 9` | label painted over hematoma, collection or fragment (removed from the ROI) |
| `--neighbors 2` | CSA/HU averaged over ±2 slices |
| `--weight-hu 0.5` | HU weight in the DFDI (article: 0.5) |
| `--area-fraction 0.70` | tunes the auto-slice heuristic (calibrate on your cases) |
| `--resample-mask` | accept a mask on another grid |
| `--no-png` | no figures |
| `--bone-exclusion` | automatic bone mask (cortex + marrow, all bones) removed from the ROI |
| `--bone-margin-px 1` | dilation of the bone mask (partial-volume rim next to the cortex) |

Reliability (ICC, as in the article):

```bash
.venv/bin/dfdi icc --csv ratings.csv --cols obs1,obs2
```

### Try without patient data

```bash
.venv/bin/python tests/phantom.py output/phantom
.venv/bin/dfdi measure --ct output/phantom/ring_ct.nii.gz --mask output/phantom/ring_deltoid.nii.gz \
    --slice-index 20 --out output/demo
```

Expected: CSA 4399.31 mm², HU 35.00, fat 10.0%.

## What it does NOT do on its own

- **Choose the slice with certainty.** The automatic slice is only a candidate. The decision is the surgeon's.
- **Exclude hematoma or fluid.** Their HU is close to muscle; they leave only if painted with the exclude label.
- **Segment the deltoid.** The mask is drawn (web app) or comes ready (command line).
- **MRI.** Not supported; HU ranges do not apply.

## Layout

```
Dockerfile, docker-compose.yml, requirements.lock   container (phase 6)
app/server.py            web server (upload, series, measure, results CSV)
app/static/index.html    viewer and drawing page (NiiVue 0.69.0)
src/dfdi/measure.py      CLI (measure, batch, icc) and the per-case flow
src/dfdi/metrics.py      CSA, HU, fat/LAMA/NAMA ranges, 3D, multi-slice, flags
src/dfdi/orientation.py  shaft axis (PCA), reorientation, candidate slice
src/dfdi/cohort.py       z-scores, DFDI, ICC
src/dfdi/bone.py         automatic bone mask (negative mask): threshold, closing per bone, fill in 3 planes
src/dfdi/qc.py           QC figures
tests/                   synthetic phantoms and tests
docs/                    article text, protocol, research, work plan
```

Patient data (`*.nii*`, `dados/`, `output/`, `saida/`) is in `.gitignore` and must never go to git.
