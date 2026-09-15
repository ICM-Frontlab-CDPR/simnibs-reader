# SimNIBS versions

`simnibs-reader` navigates SimNIBS output folders **by their layout**. It never
calls SimNIBS, and SimNIBS does not need to be installed. That makes the reader
light, but it also means the layout it assumes has to be stated — and checked
against your data.

## Supported

| SimNIBS | Layout | Status |
|---|---|---|
| **4.6** | same as 4.5 | supported |
| **4.5** | reference | supported |
| ≤ 4.1 | untested | reads in practice, not verified |
| 3.x | different | not supported — head models need `convert_3_to_4` |

Reference listings of every folder the reader touches live in
[`simnibs_reader/_simnibs-tree/`](https://github.com/ICM-Frontlab-CDPR/simnibs-reader/tree/main/simnibs_reader/_simnibs-tree),
one directory per version.

## Why 4.6 needed no change

The 4.6 release changed charm's internals without moving or renaming a single
output file: a new probabilistic atlas, AI-based reconstruction of cortical
surfaces, a new affine registration method, numpy 2. The 4.5 and 4.6 reference
trees are byte-identical.

!!! warning "One 4.6 change affects interpretation"
    Interfaces to internal air cavities now carry **their own tissue number**
    in `final_tissues`. Anything treating *any label > 0* as brain — which is
    what `ROI.complement()` does when resolving a brain mask — covers slightly
    more tissue than under 4.5.

    In practice this shifts extra-ROI statistics, and therefore the focality
    ratio, by a small amount. It is not a bug, but it means **ratios are not
    strictly comparable across a 4.5/4.6 boundary**. Keep a cohort on one
    version, or pass an explicit `brain_mask=`.

## Checking what produced your data

The version is read from the log files charm writes into `m2m_<sub>/`:

```python
import simnibs_reader as snr

seg = snr.segmentation("/path/to/m2m_0001")
seg.simnibs_version
# '4.6.0'
```

`None` means the folder records no version — older or hand-assembled folders
often don't. That is not an error, and nothing is blocked.

A version outside the supported set emits a warning on first access:

```
UserWarning: This folder was produced by SimNIBS 5.0.0; simnibs-reader has been
checked against 4.5, 4.6. Reading will be attempted anyway — the output layout
has been stable across 4.x. Please report any mismatch.
```

It warns rather than raises, because an unknown version almost always still
reads correctly and refusing would be worse than saying so once.

## When a future version moves something

If a release renames or relocates an output file:

1. add a reference tree under `_simnibs-tree/<version>/`
2. add the version to `SUPPORTED_VERSIONS` in
   `simnibs_reader/_simnibs_version.py`
3. adjust the affected glob in `core/segmentation.py`, `core/simulation.py` or
   `core/optimization.py` — those are the only places any path is written

The tests in `tests/test_simnibs_version.py` enforce that every entry in
`SUPPORTED_VERSIONS` has a reference tree, so step 1 cannot be skipped.
