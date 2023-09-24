import os; os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import tensorflow as tf
import numpy as np

import sys
import os
import json

from tensorflow.keras.optimizers import Adam


from koopmanlib.dictionary import PsiNN
from koopmanlib.param_solver import KoopmanParametricDLSolver, KoopmanLinearDLSolver, KoopmanBilinearDLSolver

config_file = sys.argv[1]
with open(config_file, 'r') as f:
    config = json.load(f)

data_path = config['data_settings']['data_path']
weights_path = config['nn_settings']['weights_path']

n_psi_train = config['nn_settings']['n_psi_train']
mu = config['data_settings']['mu']


target_dim = 2
param_dim = 1

n_psi = 1 + target_dim + n_psi_train

dict_layer_size = config['nn_settings']['dict_layer_size']
K_layer_size = config['nn_settings']['K_layer_size']

linear_epochs = config['nn_settings']['linear_epochs']
bilinear_epochs = config['nn_settings']['bilinear_epochs']
pknn_epochs = config['nn_settings']['pknn_epochs']

# Load data
dict_data = np.load(os.path.join(data_path,'vdpm_data_mu_'+str(mu)+'.npy'), allow_pickle=True)

data_x = dict_data[()]['data_x']
data_y = dict_data[()]['data_y']
data_u = dict_data[()]['data_u']

# PK-NN
dic_pk = PsiNN(layer_sizes=dict_layer_size, n_psi_train=n_psi_train)

solver_pk = KoopmanParametricDLSolver(target_dim=target_dim, param_dim=param_dim, n_psi=n_psi, dic=dic_pk)

model_pk, model_K_u_pred_pk = solver_pk.generate_model(layer_sizes=K_layer_size)

model_pk.summary()

zeros_data_y_train = tf.zeros_like(dic_pk(data_y))

model_pk.compile(optimizer=Adam(0.001),
             loss='mse')

lr_callbacks = tf.keras.callbacks.ReduceLROnPlateau(monitor='loss',
                                                    factor=0.1,
                                                    patience=200,
                                                    verbose=0,
                                                    mode='auto',
                                                    min_delta=0.0001,
                                                    cooldown=0,
                                                    min_lr=1e-12)

history = model_pk.fit(x=[data_x, data_y, data_u], 
                    y=zeros_data_y_train, 
                    epochs=pknn_epochs, 
                    batch_size=200,
                    callbacks=lr_callbacks,
                    verbose=1)


model_pk.save_weights(os.path.join(weights_path, 'model_pk_vdpm_mu_'+str(mu)+'.h5'))

# Linear Model: Dynamics is $Az +Bu$

dic_linear = PsiNN(layer_sizes=dict_layer_size, n_psi_train=n_psi_train)

solver_linear = KoopmanLinearDLSolver(dic=dic_linear, target_dim=target_dim, param_dim=param_dim, n_psi=n_psi)

model_linear = solver_linear.build_model()

zeros_data_y_train.shape

solver_linear.build(model_linear,
                    data_x,
                    data_u, 
                    data_y, 
                    zeros_data_y_train,
                    epochs=linear_epochs,
                    batch_size=200,
                    lr=0.0001,
                    log_interval=20,
                    lr_decay_factor=0.1)

model_linear.save_weights(os.path.join(weights_path, 'model_linear_vdpm_mu_'+str(mu)+'.h5'))



# Bilinear Model: Dynamics is $Az + \sum_{i=1}^{N_{u}}B_{i}zu_{i}$

dic_bilinear = PsiNN(layer_sizes=dict_layer_size, n_psi_train=n_psi_train)

solver_bilinear = KoopmanBilinearDLSolver(dic=dic_bilinear, target_dim=target_dim, param_dim=param_dim, n_psi=n_psi)

model_bilinear = solver_bilinear.build_model()

solver_bilinear.build(model_bilinear,
                    data_x,
                    data_u, 
                    data_y, 
                    zeros_data_y_train,
                    epochs=linear_epochs,
                    batch_size=200,
                    lr=0.0001,
                    log_interval=20,
                    lr_decay_factor=0.1)

model_bilinear.save_weights(os.path.join(weights_path, 'model_bilinear_vdpm_mu_'+str(mu)+'.h5'))
