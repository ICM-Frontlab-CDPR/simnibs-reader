# Standard BIDS-SimNIBS — proposition d'arborescence derivatives

## TODO remove les tasks- qui nont pas de sens 

rajouter les contraintes pour l'opti

rajouter les cond pour 

rajouter un hash pour differencier qund les param principaux sont les memes (il faudra y penser dans l'implentation de pybids-simnibs)

---

---

---

---



## Structure racine

```
derivatives/
└── simnibs/
    ├── dataset_description.json   # pipeline_version, simnibs_version, date
    ├── README.md
    ├── preps/
    ├── simulations/
    └── optimizations/
```

---

## preps/

Sorties de `charm` (et autres helpers de préparation du headmesh).

```
preps/
└── sub-{id}/
    ├── sub-{id}_m2m/                        # dossier m2m natif SimNIBS
    │   ├── sub-{id}.msh
    │   ├── T1fs_conform.nii.gz
    │   └── ...
    └── sub-{id}_prep.json                   # métadonnées de prep
```

### Convention `_prep.json`

```json
{
  "charm_version": "4.5",
  "T1_path": "../../rawdata/sub-0001/anat/sub-0001_T1w.nii.gz",
  "FLAIR_path": "../../rawdata/sub-0001/anat/sub-0001_FLAIR.nii.gz",
  "date": "2026-05-22",
  "qc_pass": true,
  "notes": ""
}
```

---

## simulations/

Champs électriques simulés, une entrée par sujet × condition × montage.

```
simulations/
└── sub-{id}/
    └── sub-{id}_task-{task}_cond-{cond}_montage-{montage}_sim/
        ├── sub-{id}_task-{task}_cond-{cond}_montage-{montage}_sim.json
        ├── sub-{id}_task-{task}_cond-{cond}_montage-{montage}_E-field.msh
        ├── sub-{id}_task-{task}_cond-{cond}_montage-{montage}_normE.nii.gz  # optionnel
        └── sub-{id}_task-{task}_cond-{cond}_montage-{montage}_E.nii.gz      # optionnel
```

### Exemple concret

```
simulations/
└── sub-0001/
    └── sub-0001_task-fef_cond-M1_montage-HDTDCS4x1_sim/
        ├── sub-0001_task-fef_cond-M1_montage-HDTDCS4x1_sim.json
        ├── sub-0001_task-fef_cond-M1_montage-HDTDCS4x1_E-field.msh
        ├── sub-0001_task-fef_cond-M1_montage-HDTDCS4x1_normE.nii.gz
        └── sub-0001_task-fef_cond-M1_montage-HDTDCS4x1_E.nii.gz
```

### Convention `_sim.json`

```json
{
  "task": "fef",
  "cond": "M1",
  "montage": "HDTDCS4x1",
  "current_mA": 1.0,
  "electrode_size_mm": 10,
  "electrode_shape": "circular",
  "mesh_path": "../../preps/sub-0001/sub-0001_m2m/sub-0001.msh",
  "simnibs_version": "4.5",
  "date": "2026-05-22",
  "qc_pass": true
}
```

### Entités BIDS utilisées

| entité      | valeurs possibles         | exemple                                |
| ------------ | ------------------------- | -------------------------------------- |
| `task-`    | paradigme expérimental   | `fef`, `motor`, `dlpfc`          |
| `cond-`    | condition                 | `M1`, `sham`, `active`           |
| `montage-` | configuration électrodes | `HDTDCS4x1`, `bilateral`, `ring` |

---

## optimizations/

Résultats d'optimisation ADM / TDCS, une entrée par sujet × cible × méthode.

```
optimizations/
└── sub-{id}/
    └── sub-{id}_task-{task}_target-{roi}_method-{method}_opti/
        ├── sub-{id}_task-{task}_target-{roi}_method-{method}_opti.json
        ├── sub-{id}_task-{task}_target-{roi}_method-{method}_optweights.csv
        ├── sub-{id}_task-{task}_target-{roi}_method-{method}_E-field.msh   # optionnel
        └── sub-{id}_task-{task}_target-{roi}_method-{method}_normE.nii.gz  # optionnel
```

### Exemple concret

```
optimizations/
└── sub-0001/
    └── sub-0001_task-fef_target-M1_method-adm_opti/
        ├── sub-0001_task-fef_target-M1_method-adm_opti.json
        ├── sub-0001_task-fef_target-M1_method-adm_optweights.csv
        └── sub-0001_task-fef_target-M1_method-adm_normE.nii.gz
```

### Convention `_opti.json`

```json
{
  "task": "fef",
  "target_roi": "M1",
  "method": "adm",
  "n_electrodes": 5,
  "max_current_mA": 1.0,
  "focality_radius_mm": 20,
  "mesh_path": "../../preps/sub-0001/sub-0001_m2m/sub-0001.msh",
  "simnibs_version": "4.5",
  "date": "2026-05-22",
  "qc_pass": true
}
```

### Convention `_optweights.csv`

```csv
electrode_label,x,y,z,current_mA
E1,-45.2,12.3,67.1,0.8
E2,-52.1,8.7,71.4,-0.2
E3,-38.4,15.2,63.8,-0.2
E4,-48.9,5.1,69.2,-0.2
ref,0.0,0.0,0.0,-0.2
```

### Entités BIDS utilisées

| entité     | valeurs possibles       | exemple                    |
| ----------- | ----------------------- | -------------------------- |
| `task-`   | paradigme expérimental | `fef`, `motor`         |
| `target-` | ROI cible               | `M1`, `DLPFC`, `FEF` |
| `method-` | algorithme              | `adm`, `tdcs`, `mni` |

---

## Points ouverts

- Ajouter `ses-` si plusieurs timepoints par sujet
- Les NIfTI (normE, E) : systématiques ou à la demande ?
- Inclure un `participants.tsv` au niveau `simnibs/` avec les QC globaux ?
