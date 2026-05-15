


#use case
import simnibs-bids as snb   # higher level : gerer les experiences multiples etc
import simnibs-reader as snr # one 



snb.query( by-targets , by-a-simu-modality) 
#--> renvoie les listes de folders concernées (c'est peutetre pas tres utile si les differentes simulations sont bine rangées: )
# path : simnibs-simu/simnibs-param/simu-subject-1...


--- association to a directory
results =snr.simulation('path_simu')

results = snr.optimization('path_opti')

results = snr.segmentation('path_m2m')


# ---puis la sélection de file
# quels sont les calculs qui sont multifiles ? est-ce que c'est mportant de les inclures dans l'architecture des maintenant ?

files = results.magnE

# ---puis la possibilité de faire tout ce qui est deja defini dans simnibs-analyze

file.getROI().postprocess().save_as()
# files.getROI().postprocess().save_as() ?


# je vais tester l'utlisation principale maintenant : pourrais tu me reecrire la config stp mais pour le dataset stim SD./Users/hippolyte.dreyfus/Desktop/_stimSD/Data/derivatives/mri/simnibs-simucest ce .txt de simnibs modular qui a été utilisé :/Users/hippolyte.dreyfus/Documents/simnibs-modular/config/stimSD/simulation_stimSD.txt
# Attention il va avoir une problematique importante a gerer, on va y aller etape par etape :jusqu'a maintenant le _io_pipeline.py considère que tous les fichiers sont au sein d'un seul directory simnibs-...Mais maintenant je veux differencier-simnibs-preps :les resultats de charm pour la segmentation-simnibs-simu : les resultats de simulation ou optimisation-simnibs-analyze : les etapes jusqu'a lextraction de valeurs dans des csvs-et results pour les stats basiques que fait simnibs analyze



# ———————
# Simnibs analyze :
# - outil de querying d’un sous ensemble des folder de simulation (based on name folder or other ?)
# - outil reader d’output (au niveau d’un folder de simulation, )