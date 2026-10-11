import tensorflow as tf
print('TensorFlow version:', tf.__version__)
print('TF path:', tf.__file__)

import keras
print('Keras version:', keras.__version__)

import google.protobuf
print('Protobuf version:', google.protobuf.__version__)

model = keras.models.load_model('ml_models/emotion_model.keras')
print('Model loaded successfully')
print('Input shape:', model.input_shape)
print('Output shape:', model.output_shape)
