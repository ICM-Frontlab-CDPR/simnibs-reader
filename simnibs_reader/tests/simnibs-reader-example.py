
#### definition of nbasic use cases
# test de l'outil reader d’output (au niveau d’un folder de simulation, )


import simnibs-reader as snr # one 
##import simnibs  # ?? IMPORTANT DECISION Is it more secure to not use this dependency which is not build in pip (because of simnibs charm binaries ?)



#### A--- Loaders for 3 differents type of results directory :
results =snr.simulation('path_simu')

results = snr.optimization('path_opti')

results = snr.segmentation('path_m2m')




#### B--- efield-like nifti files extraction (4 possible steps)


# choose your modality
efield_file = results.magnE #pouvoir choisir mni ou subject

# extract your ROI
efields_ROI = efield_file.getROI(by-targets // with a specific nifti mask  // using a mask from freesurfer/spm results)

# postprocess 
efields_PP = efields_ROI.postprocess( filter= , smoothing= , ... )

#save your data before doing stats
efields_PP.save( metrics=[mean,median,gaussian,...], format= tsv)








