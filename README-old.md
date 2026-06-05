-doit récupérer toute la logique d'input contenu dans io_pipeline de simnibs-analyze pour la réinjecter ensuite sous forme d'une dépdance propre.


# simnibs-reader

Python API for easy access of simnibs results with 3 level of organization.


**Simnibs-bids-structure :**

A standardization of the name of the simnibs folders (with bids logic) for multi-simulation/optimiation experiments... check if this is a commun use or not ? because it could lead to overuseof "simulation" rather than "optimization" expe... So what could be the real usecase of this ?

(TO DECIDE : hierarchy of simnibs simulation parameters : electrodes_currents_conductivities (see Simnibs Data Structures)


**Description of the files accessible in a folder of simnibs results:**

*Folder type : simulation folder / optimization folder /m2m folder*

- les resultats E-nifti en particulier
- les surfaces ?
- dans m2m... les fichiers de preparation de simulations (pour pouvoir spécialisé la simulation)

**Description of the variables extractable , for each files :**

--> For each nifti file produced:

1- ROI-based easy querying [IMPORTANT : Checker le tool qui permet de creer des ROIs aisement (en native comme en mni)]

2- postprocessing filters (to check si ça doit rester dans analyze ou si c'est necessairement dans le reader !?)

3- metrics extractions

- efield-niftii specific : mean
- label_preps specific : total amount of a specific label + width / length measure (check the nilearn tool for this)

--> other type of file ?


This querying tool allows both "a la volée python traitement" ou des save propres de metrics utile pour des analyses futures.
