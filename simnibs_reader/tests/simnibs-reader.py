
#### definition of nbasic use cases
# test de l'outil reader d’output (au niveau d’un folder de simulation, )


import simnibs-reader as snr # one 
import simnibs ?? #IMPORTANT DECISION Is it secure to use this dependency which is not build in pip (because of simnibs charm binaries ?)



#### A--- Loaders for 3 differents type of results directory :
results =snr.simulation('path_simu')

results = snr.optimization('path_opti')

results = snr.segmentation('path_m2m')




#### B--- efield-like nifti files extraction (4 possible steps)


# choose your modality
efield_file = results.get_file('magnE')

# extract your ROI
efields_ROI = efield_file.getROI(by-targets // with a specific nifti mask  // using a mask from freesurfer/spm results)

# postprocess 
efields_PP = efields_ROI.postprocess( filter= , smoothing= , ... )

#save your data before doing stats
efields_PP.save( metrics=[mean,median,gaussian,...], format= tsv)


#### ZZ--- simnibs-analyze is a pipeline which make all the basic stats of a simnibs simulation, using simnibs-reader
# puis la possibilité de faire tout ce qui est deja defini dans simnibs-analyze




# je vais tester l'utlisation principale maintenant : pourrais tu me reecrire la config stp mais pour le dataset stim SD./Users/hippolyte.dreyfus/Desktop/_stimSD/Data/derivatives/mri/simnibs-simucest ce .txt de simnibs modular qui a été utilisé :/Users/hippolyte.dreyfus/Documents/simnibs-modular/config/stimSD/simulation_stimSD.txt
# Attention il va avoir une problematique importante a gerer, on va y aller etape par etape :jusqu'a maintenant le _io_pipeline.py considère que tous les fichiers sont au sein d'un seul directory simnibs-...Mais maintenant je veux differencier-simnibs-preps :les resultats de charm pour la segmentation-simnibs-simu : les resultats de simulation ou optimisation-simnibs-analyze : les etapes jusqu'a lextraction de valeurs dans des csvs-et results pour les stats basiques que fait simnibs analyze



