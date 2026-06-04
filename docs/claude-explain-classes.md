<thinking>
The user wants a quick explanation of how the modules interact. Let me give a clear, concise overview.
</thinking>

## Architecture du module — flux de données

```
snr.simulation("path/")
        │
        ▼
 SimulationResult          ← core/simulation.py
 (hérite SimNIBSResult)    ← core/_base.py
        │
        │  results.magnE   (cached_property)
        ▼
 EFieldAccessor            ← efield/accessor.py
 (wrapper lazy NIfTI)
        │
        │  .get_roi(mask=, coords=, radius=)
        ▼
 ROIExtractor              ← efield/roi.py
 (construit le masque)
        │
        │  .extract()
        ▼
 ROIResult                 ← efield/roi.py
 (values 1D + mask_img)
        │
        │  .postprocess(smooth_fwhm=, outlier_method=)
        ▼
 Preprocessor.run()        ← efield/postprocess.py
        │
        ▼
 CleanedResult             ← efield/postprocess.py
 (values nettoyées + cleaned_img + masked_img)
        │
        │  .save() / .save_nifti()
        ▼
 io/export.py  /  io/nifti.py
```

---

### Les 3 niveaux de responsabilité

**`core/`** — *"où sont mes fichiers ?"*

- Connaît la structure des dossiers SimNIBS sur le disque
- Expose des `cached_property` qui retournent des `EFieldAccessor` (jamais des arrays)
- Ne fait aucun calcul, ne charge aucune donnée NIfTI

**`efield/`** — *"que contiennent mes fichiers ?"*

- `accessor.py` : charge le NIfTI une fois, expose `.data`, `.affine`, `.shape`
- `roi.py` : construit un masque (path / sphère / atlas) et l'applique → valeurs 1D
- `postprocess.py` : lisse et nettoie ces valeurs → les remet en volume 3D
- `stats.py` : calcule les stats sur les valeurs 1D, sans dépendance nibabel

**`io/`** — *"comment je sauvegarde ?"*

- `nifti.py` : read/write NIfTI, rien de plus
- `export.py` : stats dict → TSV/CSV

---

### Le principe clé : **chaque objet tient une référence à son parent**

```python
CleanedResult.source      # → ROIResult
ROIResult.efield          # → EFieldAccessor
ROIResult.mask_img        # → nib.Nifti1Image (le masque utilisé)
EFieldAccessor.path       # → Path (le fichier sur le disque)
```

Ce qui permet à `Preprocessor.run()` de remonter jusqu'à l'image originale (`roi_result.efield.img`) pour appliquer le smoothing *avant* le masking, sans que l'utilisateur ait à repasser les arguments.
