Voici le résumé de ce que contient ce dossier `sub-0003` FreeSurfer :

## `mri/` — volumes 3D

Les fichiers clés en `.mgz` (format FreeSurfer, équivalent NIfTI) :

| fichier                     | contenu                                                         |
| --------------------------- | --------------------------------------------------------------- |
| `T1.mgz`                  | T1 conformé (base de tout)                                     |
| `brain.mgz`               | cerveau extrait (skull-stripped)                                |
| `aparc+aseg.mgz`          | **parcellisation principale**— atlas DK + sous-corticaux |
| `aparc.a2009s+aseg.mgz`   | parcellisation Destrieux (plus fine)                            |
| `aparc.DKTatlas+aseg.mgz` | atlas DKT                                                       |
| `wm.mgz`                  | masque matière blanche                                         |
| `ribbon.mgz`              | ruban cortical (entre white et pial)                            |
| `FLAIR.mgz`               | FLAIR intégré (ton sujet a du FLAIR ✓)                       |
| `transforms/synthmorph*/` | **warps vers MNI152**— clé pour matcher SimNIBS         |

---

## `surf/` — surfaces corticales

Pour chaque hémisphère (`lh.` / `rh.`) :

| fichier                        | contenu                                             |
| ------------------------------ | --------------------------------------------------- |
| `lh.pial`→`lh.pial.FLAIR` | surface piale (affinée avec FLAIR ✓)              |
| `lh.white`                   | surface matière blanche                            |
| `lh.inflated`                | surface gonflée (visualisation)                    |
| `lh.thickness`               | épaisseur corticale par vertex                     |
| `lh.sphere.reg`              | surface sphérique (pour registration inter-sujets) |

---

## `label/` — annotations parcellaires

| fichier                   | contenu                      |
| ------------------------- | ---------------------------- |
| `lh.aparc.annot`        | labels DK par vertex surface |
| `lh.aparc.a2009s.annot` | labels Destrieux par vertex  |
| `lh.BA*.label`          | aires de Brodmann ex-vivo    |
| `lh.cortex.label`       | masque cortex pur            |

---

## `stats/` — statistiques morphométriques

| fichier              | contenu                                 |
| -------------------- | --------------------------------------- |
| `lh.aparc.stats`   | épaisseur, aire, volume par région DK |
| `aseg.stats`       | volumes structures sous-corticales      |
| `synthseg.vol.csv` | volumes SynthSeg (robuste)              |

---
