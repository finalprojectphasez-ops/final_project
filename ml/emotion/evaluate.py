import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    test_dir = 'dataset/test'
    model_path = 'emotion_model.keras'
    
    if not os.path.exists(test_dir):
        print("Test dataset not found. Please run preprocess.py first.")
        return
        
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}. Please train the model first.")
        return

    print("Loading model...")
    model = tf.keras.models.load_model(model_path)

    test_datagen = ImageDataGenerator(rescale=1./255)
    
    batch_size = 64
    test_generator = test_datagen.flow_from_directory(
        test_dir,
        target_size=(48, 48),
        color_mode='grayscale',
        batch_size=batch_size,
        class_mode='categorical',
        shuffle=False
    )

    print("Evaluating model...")
    predictions = model.predict(test_generator, steps=np.ceil(test_generator.samples / batch_size))
    y_pred = np.argmax(predictions, axis=1)
    y_true = test_generator.classes

    class_labels = list(test_generator.class_indices.keys())

    # Metrics
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average='weighted')
    rec = recall_score(y_true, y_pred, average='weighted')
    f1 = f1_score(y_true, y_pred, average='weighted')

    print("\n--- Evaluation Metrics ---")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    
    print("\n--- Classification Report ---")
    print(classification_report(y_true, y_pred, target_names=class_labels))

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=class_labels, yticklabels=class_labels)
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig('confusion_matrix.png')
    
    print("Confusion matrix saved to confusion_matrix.png")

if __name__ == "__main__":
    main()
