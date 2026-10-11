import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# Paths
dataset_dir = os.path.join(os.path.dirname(__file__), 'dataset', 'processed')
model_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'ml_models')
os.makedirs(model_dir, exist_ok=True)

model_path = os.path.join(model_dir, 'gaze_model.keras')
history_path = os.path.join(model_dir, 'gaze_training_history.json')

def load_data():
    print("Loading data...")
    X_train = np.load(os.path.join(dataset_dir, 'X_train.npy'))
    y_train = np.load(os.path.join(dataset_dir, 'y_train.npy'))
    X_val = np.load(os.path.join(dataset_dir, 'X_val.npy'))
    y_val = np.load(os.path.join(dataset_dir, 'y_val.npy'))
    X_test = np.load(os.path.join(dataset_dir, 'X_test.npy'))
    y_test = np.load(os.path.join(dataset_dir, 'y_test.npy'))
    return X_train, y_train, X_val, y_val, X_test, y_test

def build_model(input_shape):
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
        BatchNormalization(),
        MaxPooling2D((2, 2)),
        
        Conv2D(64, (3, 3), activation='relu'),
        BatchNormalization(),
        MaxPooling2D((2, 2)),
        
        Conv2D(128, (3, 3), activation='relu'),
        BatchNormalization(),
        MaxPooling2D((2, 2)),
        
        Flatten(),
        Dense(256, activation='relu'),
        Dropout(0.4),
        Dense(128, activation='relu'),
        Dropout(0.3),
        
        # Regression output: 2 units (Pitch, Yaw)
        Dense(2, activation='linear')
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

if __name__ == "__main__":
    X_train, y_train, X_val, y_val, X_test, y_test = load_data()
    
    print(f"X_train shape: {X_train.shape}")
    print(f"y_train shape: {y_train.shape}")
    print(f"X_val shape: {X_val.shape}")
    print(f"y_val shape: {y_val.shape}")
    print(f"X_test shape: {X_test.shape}")
    print(f"y_test shape: {y_test.shape}")
    
    model = build_model(X_train.shape[1:])
    model.summary()
    
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
        ModelCheckpoint(model_path, monitor='val_loss', save_best_only=True)
    ]
    
    print("Starting training...")
    # Using 10 epochs max and large batch size to speed up training, since data is large (103k)
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=20,
        batch_size=128,
        callbacks=callbacks,
        verbose=1
    )
    
    # Save history
    history_dict = history.history
    # Convert types to standard python types for JSON serialization
    for k, v in history_dict.items():
        history_dict[k] = [float(val) for val in v]
        
    with open(history_path, 'w') as f:
        json.dump(history_dict, f, indent=4)
        
    print(f"Model saved to: {model_path}")
    print(f"History saved to: {history_path}")
