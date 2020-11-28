import pickle
import scipy.io as sio 
import os
#os.chdir("../")

import survivalnet as sn
#os.chdir("examples/")

# Integrated models. 
# Defines model/dataset pairs.
ModelPaths = ['results/']
Models = ['final_model']
Data = ['../data/Brain_Integ.mat']

# Loads datasets and performs feature analysis.
for i, Path in enumerate(ModelPaths):
	print(enumerate(ModelPaths))
	print("i is ", i, '\n', "Path is", Path)
	# Loads normalized data.
	XXXX = sio.loadmat(Data[i], mat_dtype=True)
	print(XXXX.keys())

	# Extracts relevant values.
	Samples = XXXX['Patients']
	Normalized = XXXX['Integ_X'].astype('float32')
	Raw = XXXX['Integ_X_raw'].astype('float32')
	Symbols = XXXX['Integ_Symbs']
	Survival = XXXX['Survival']
	Censored = XXXX['Censored']

	# Loads model.
	print(Models[i])
	path = Path + Models[i]
	print(path, "is the path")
	print("Opening")
	f = open(Path + Models[i], 'rb')
	print("Opened")
	Model = pickle.load(f)
	f.close()
	
	sn.analysis.FeatureAnalysis(Model, Normalized, Raw, Symbols,
								Survival, Censored,
								Tau=5e-2, Path=Path)
	print("Done with ModelAnalysis.py")
