# SimNIBS reference trees

Reference listings of the folders SimNIBS produces, one directory per version.
They document what this reader navigates; no code reads them.

| Version | Layout |
|---|---|
| `4.5/` | reference |
| `4.6/` | identical to 4.5 |

The 4.6 release changed charm internals — a new probabilistic atlas, AI-based
cortical surface reconstruction, a new affine registration method, numpy 2 —
without moving or renaming any output file. The two trees are therefore
byte-identical, and kept as separate directories so that a future version which
*does* move something has an obvious place to land.

One 4.6 change alters interpretation rather than location: interfaces to
internal air cavities now carry their own tissue number in `final_tissues`.
Masks built as "any label > 0" — as `ROI.complement()` does — cover slightly
more than under 4.5.

Detection lives in `simnibs_reader/_simnibs_version.py`, which reads the
version from charm's own log files.
