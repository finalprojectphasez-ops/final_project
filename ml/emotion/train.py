import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
import matplotlib.pyplot as plt

def set_seeds(seed=42):
    np.random.seed(seed)
    tf.random.set_seed(seed)

def build_model(input_shape=(48, 48, 1), num_classes=7):
    model = Sequential([
        Conv2D(64, (3, 3), activation='relu', input_shape=input_shape, padding='same'),
        BatchNormalization(),
        Conv2D(64, (3, 3), activation='relu', padding='same'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.25),

        Conv2D(128, (3, 3), activation='relu', padding='same'),
        BatchNormalization(),
        Conv2D(128, (3, 3), activation='relu', padding='same'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.25),

        Conv2D(256, (3, 3), activation='relu', padding='same'),
        BatchNormalization(),
        Conv2D(256, (3, 3), activation='relu', padding='same'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.25),

        Flatten(),
        Dense(512, activation='relu'),
        BatchNormalization(),
        Dropout(0.5),
        Dense(num_classes, activation='softmax')
    ])
    
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])
    return model

def main():
    set_seeds(42)
    
    # 17. Use paths based on the project location / __file__
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    
    dataset_dir = os.path.join(script_dir, 'dataset', 'processed')
    models_dir = os.path.join(project_root, 'backend', 'ml_models')
    
    # 15. Create directory if it doesn't exist
    os.makedirs(models_dir, exist_ok=True)
    
    # 1. Load preprocessed train data
    x_train_path = os.path.join(dataset_dir, 'X_train.npy')
    y_train_path = os.path.join(dataset_dir, 'y_train.npy')
    
    if not os.path.exists(x_train_path) or not os.path.exists(y_train_path):
        print(f"Error: Processed dataset not found at {dataset_dir}")
        return
        
    print("Loading preprocessed dataset...")
    # 2. X_test.npy is explicitly omitted
    X_full = np.load(x_train_path)
    y_full = np.load(y_train_path)
    
    # Ensure shape is (N, 48, 48, 1) to match input shape
    if len(X_full.shape) == 3:
        X_full = np.expand_dims(X_full, axis=-1)
        
    num_classes = 7
    emotions = {0: 'angry', 1: 'disgust', 2: 'fear', 3: 'happy', 4: 'neutral', 5: 'sad', 6: 'surprise'}
    
    # 3. Create a validation split from the training data (Stratified)
    X_train, X_val, y_train, y_val = train_test_split(
        X_full, y_full, test_size=0.2, random_state=42, stratify=y_full
    )
    
    # 6. Handle class imbalance
    class_weights = compute_class_weight(
        class_weight='balanced',
        classes=np.unique(y_train),
        y=y_train
    )
    class_weight_dict = dict(enumerate(class_weights))
    
    # 10. Convert labels to one-hot encoding before training
    y_train_cat = to_categorical(y_train, num_classes=num_classes)
    y_val_cat = to_categorical(y_val, num_classes=num_classes)
    
    # 19. Print useful information
    print("\n--- Dataset Information ---")
    print(f"Input Shape: {X_train.shape[1:]}")
    print(f"Number of Classes: {num_classes}")
    print(f"Training Samples: {len(X_train)}")
    print(f"Validation Samples: {len(X_val)}")
    
    print("\n--- Class Distribution (Train) ---")
    unique_classes, counts = np.unique(y_train, return_counts=True)
    for cls, count in zip(unique_classes, counts):
        print(f"  {emotions[cls]}: {count}")
        
    print("\n--- Calculated Class Weights ---")
    for cls, weight in class_weight_dict.items():
        print(f"  {emotions[cls]}: {weight:.4f}")
    
    # 5. Data Augmentation (no rescale as data is already 0-1)
    train_datagen = ImageDataGenerator(
        rotation_range=15,
        width_shift_range=0.15,
        height_shift_range=0.15,
        shear_range=0.15,
        zoom_range=0.15,
        horizontal_flip=True
    )
    
    batch_size = 64
    train_generator = train_datagen.flow(X_train, y_train_cat, batch_size=batch_size)
    
    # 8. & 9. CNN Architecture with input shape (48, 48, 1) and output 7
    model = build_model(input_shape=X_train.shape[1:], num_classes=num_classes)
    model.summary()
    
    model_save_path = os.path.join(models_dir, 'emotion_model.keras')
    history_save_path = os.path.join(models_dir, 'emotion_training_history.json')
    
    # 12. EarlyStopping, 13. ModelCheckpoint, 14. Monitor val_accuracy
    early_stop = EarlyStopping(monitor='val_accuracy', mode='max', patience=10, restore_best_weights=True, verbose=1)
    checkpoint = ModelCheckpoint(model_save_path, monitor='val_accuracy', mode='max', save_best_only=True, verbose=1)
    reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1)
    
    print("\nStarting training...")
    history = model.fit(
        train_generator,
        epochs=50,
        validation_data=(X_val, y_val_cat),
        class_weight=class_weight_dict,
        callbacks=[early_stop, checkpoint, reduce_lr]
    )
    
    # 16. Save training history
    history_dict = {k: [float(val) for val in v] for k, v in history.history.items()}
    with open(history_save_path, 'w') as f:
        json.dump(history_dict, f, indent=4)
        
    print(f"\nTraining complete. Model saved to {model_save_path}")
    print(f"History saved to {history_save_path}")

if __name__ == "__main__":
    main()
