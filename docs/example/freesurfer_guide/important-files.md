## Ce qui est le plus utile pour matcher avec SimNIBS

**Pour masquer les champs E :**

```
mri/aparc+aseg.mgz          → labels volumétriques à resampler sur le NIfTI E-field
mri/transforms/synthmorph*/ → warps MNI152 pour aligner les espaces
```

**Pour une analyse surfacique :**

```
surf/lh.pial + label/lh.aparc.annot → projeter le E-field sur la surface corticale
```

Le fait que tu aies le FLAIR intégré (`lh.pial.FLAIR`) et les warps SynthMorph vers MNI152 est un bon signe — la qualité de segmentation et l'alignement MNI seront meilleurs.
