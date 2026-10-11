"""
emotion_v2/train_v2.py
======================
Improved emotion recognition — MobileNetV2 transfer learning experiment.

ARCHITECTURE RATIONALE
----------------------
- MobileNetV2 (ImageNet pretrained) chosen over EfficientNetB0 / EfficientNetV2B0:
    * Lowest param count (2.26M backbone) => fastest real-time inference on CPU
    * ImageNet pretrained weights available and downloaded successfully
    * Well-studied on face-centric tasks
- Input: 96x96 RGB -- upscaled from 48x48 grayscale (gray->RGB by repeating channel).
    * At 48x48 the backbone's spatial output is 2x2 -- too spatially collapsed for
      meaningful transfer features.  96x96 gives 3x3 output, substantially better.
    * Still a 4x area increase from 48x48, keeping preprocessing fast.
- Two-phase training:
    Phase 1: Freeze backbone -- train only classifier head (8 epochs warm-up).
    Phase 2: Unfreeze top-N layers -- fine-tune end-to-end with low LR.

DATA LEAKAGE PREVENTION
------------------------
- X_test.npy / y_test.npy loaded at the END only for final evaluation.
- All augmentation applied to train split ONLY.
- Validation split (20% stratified from train) used for model selection.
- Checkpoint saved on best val_accuracy. Early stopping on val_accuracy.

IMBALANCE STRATEGY
------------------
- disgust: 436 samples vs happy: 7215 (16.5:1 ratio)
- compute_class_weight('balanced') => class weights passed to model.fit
- Random oversampling of minority classes before augmentation.

AUGMENTATION (train only)
--------------------------
- Random horizontal flip
- Random rotation 15 deg
- Width/height shift 10%
- Zoom 10%
- Brightness 20%
- NO augmentation on validation or test.
"""

import os, json, time, random
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, f1_score, precision_score, recall_score
)

# Reproducibility
SEED = 42
os.environ['PYTHONHASHSEED'] = str(SEED)
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

# Suppress noisy TF logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Paths
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, 'ml', 'emotion', 'dataset', 'processed')
MODELS_DIR    = os.path.join(PROJECT_ROOT, 'backend', 'ml_models')
OUTPUT_DIR    = os.path.join(SCRIPT_DIR, 'outputs')
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL_SAVE_PATH   = os.path.join(MODELS_DIR, 'emotion_model_v2.keras')
HISTORY_SAVE_PATH = os.path.join(OUTPUT_DIR, 'training_history_v2.json')
REPORT_SAVE_PATH  = os.path.join(OUTPUT_DIR, 'eval_report_v2.json')
CM_SAVE_PATH      = os.path.join(OUTPUT_DIR, 'confusion_matrix_v2.npy')

# Constants
EMOTIONS      = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
NUM_CLASSES   = 7
IMG_SIZE      = 96
BATCH_SIZE    = 32
VAL_SPLIT     = 0.20
PHASE1_EPOCHS = 8
PHASE2_EPOCHS = 60
UNFREEZE_FROM = 100


def load_data():
    print("Loading FER-2013 training data...")
    X = np.load(os.path.join(PROCESSED_DIR, 'X_train.npy'))
    y = np.load(os.path.join(PROCESSED_DIR, 'y_train.npy'))
    print("  Loaded: X={}, y={}".format(X.shape, y.shape))
    return X, y


def load_test_data():
    """Load test data -- called ONLY at final evaluation step."""
    print("Loading FER-2013 test data (final evaluation only)...")
    X = np.load(os.path.join(PROCESSED_DIR, 'X_test.npy'))
    y = np.load(os.path.join(PROCESSED_DIR, 'y_test.npy'))
    print("  Loaded: X={}, y={}".format(X.shape, y.shape))
    return X, y


def preprocess_batch(X_gray):
    """
    Input:  float32 array (N, 48, 48) in [0, 1]
    Output: float32 array (N, 96, 96, 3) in [0, 1]
    """
    X_rgb = np.stack([X_gray, X_gray, X_gray], axis=-1)
    X_resized = tf.image.resize(X_rgb, [IMG_SIZE, IMG_SIZE]).numpy()
    return X_resized.astype(np.float32)


def oversample(X, y, target_ratio=2.5):
    """
    Oversample classes with count < (max_count / target_ratio).
    Applied to TRAIN split ONLY.
    """
    counts = np.bincount(y, minlength=NUM_CLASSES)
    max_count = counts.max()
    threshold = int(max_count / target_ratio)

    X_aug_list, y_aug_list = [X], [y]
    for cls in range(NUM_CLASSES):
        cls_idx = np.where(y == cls)[0]
        n = counts[cls]
        if n < threshold:
            n_needed = threshold - n
            chosen = np.random.choice(cls_idx, size=n_needed, replace=True)
            X_extra = X[chosen] + np.random.normal(0, 0.005, X[chosen].shape).astype(np.float32)
            X_extra = np.clip(X_extra, 0.0, 1.0)
            X_aug_list.append(X_extra)
            y_aug_list.append(np.full(n_needed, cls, dtype=y.dtype))
            print("  Oversampled '{}': {} -> {}".format(EMOTIONS[cls], n, n + n_needed))

    X_out = np.concatenate(X_aug_list, axis=0)
    y_out = np.concatenate(y_aug_list, axis=0)
    idx = np.random.permutation(len(y_out))
    return X_out[idx], y_out[idx]


def make_dataset(X, y, augment=False, shuffle=True):
    """Build a tf.data.Dataset from numpy arrays."""
    y_cat = tf.keras.utils.to_categorical(y, NUM_CLASSES).astype(np.float32)
    ds = tf.data.Dataset.from_tensor_slices((X, y_cat))
    if shuffle:
        ds = ds.shuffle(len(X), seed=SEED, reshuffle_each_iteration=True)
    if augment:
        aug_layers = tf.keras.Sequential([
            tf.keras.layers.RandomFlip("horizontal", seed=SEED),
            tf.keras.layers.RandomRotation(15/360, seed=SEED),
            tf.keras.layers.RandomZoom((-0.10, 0.10), seed=SEED),
            tf.keras.layers.RandomTranslation(0.10, 0.10, seed=SEED),
            tf.keras.layers.RandomBrightness(0.20, value_range=(0.0, 1.0), seed=SEED),
            tf.keras.layers.RandomContrast(0.15, seed=SEED),
        ])
        ds = ds.map(
            lambda x, lbl: (tf.clip_by_value(aug_layers(x, training=True), 0.0, 1.0), lbl),
            num_parallel_calls=tf.data.AUTOTUNE
        )
    ds = ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    return ds


def build_model():
    """MobileNetV2 backbone + custom head."""
    backbone = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights='imagenet'
    )
    backbone.trainable = False

    inputs = tf.keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name='image_input')
    # MobileNetV2 expects inputs in [-1, 1]; our data is [0, 1]
    x = tf.keras.layers.Rescaling(scale=2.0, offset=-1.0, name='mobilenet_preprocess')(inputs)
    x = backbone(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D(name='gap')(x)
    x = tf.keras.layers.BatchNormalization(name='bn_head')(x)
    x = tf.keras.layers.Dropout(0.4, name='drop1')(x)
    x = tf.keras.layers.Dense(
        256, activation='relu', name='fc1',
        kernel_regularizer=tf.keras.regularizers.l2(1e-4)
    )(x)
    x = tf.keras.layers.BatchNormalization(name='bn_fc')(x)
    x = tf.keras.layers.Dropout(0.3, name='drop2')(x)
    outputs = tf.keras.layers.Dense(NUM_CLASSES, activation='softmax', name='predictions')(x)

    model = tf.keras.Model(inputs, outputs)
    return model, backbone


def compile_model(model, lr, label_smoothing=0.1):
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=label_smoothing),
        metrics=['accuracy']
    )


def main():
    start_time = time.time()
    print("=" * 60)
    print("  PreMock AI -- Emotion Model v2 Training")
    print("  Architecture: MobileNetV2 + Transfer Learning")
    print("=" * 60)

    X_raw, y_raw = load_data()

    print("\n=== Original Class Distribution (Train) ===")
    counts_orig = np.bincount(y_raw, minlength=NUM_CLASSES)
    for i, (em, c) in enumerate(zip(EMOTIONS, counts_orig)):
        print("  {:10s}: {:5d} ({:.1f}%)".format(em, c, c/len(y_raw)*100))

    # Stratified train/val split
    X_train_raw, X_val_raw, y_train, y_val = train_test_split(
        X_raw, y_raw, test_size=VAL_SPLIT, random_state=SEED, stratify=y_raw
    )
    print("\n  Train: {}, Val: {}".format(len(y_train), len(y_val)))

    # Oversample minority classes in train split only
    print("\n=== Oversampling Minority Classes (train only) ===")
    X_train_os, y_train_os = oversample(X_train_raw, y_train, target_ratio=2.5)
    print("  After oversampling -- Train: {}".format(len(y_train_os)))

    # Preprocess to 96x96 RGB
    print("\n=== Preprocessing: 48x48 gray -> 96x96 RGB ===")
    print("  Processing train set...")
    X_train = preprocess_batch(X_train_os)
    print("  Processing val set...")
    X_val   = preprocess_batch(X_val_raw)
    print("  X_train: {}, dtype={}".format(X_train.shape, X_train.dtype))
    print("  X_val:   {}, dtype={}".format(X_val.shape, X_val.dtype))

    # Class weights
    class_weights_arr = compute_class_weight(
        class_weight='balanced', classes=np.arange(NUM_CLASSES), y=y_train_os
    )
    class_weight_dict = {i: w for i, w in enumerate(class_weights_arr)}
    print("\n=== Class Weights ===")
    for i, (em, w) in enumerate(zip(EMOTIONS, class_weights_arr)):
        print("  {:10s}: {:.4f}".format(em, w))

    # Build datasets
    train_ds = make_dataset(X_train, y_train_os, augment=True,  shuffle=True)
    val_ds   = make_dataset(X_val,   y_val,       augment=False, shuffle=False)

    # PHASE 1: Head-only training
    print("\n" + "=" * 60)
    print("  PHASE 1 -- Warm-up: Training head only (backbone frozen)")
    print("=" * 60)

    model, backbone = build_model()
    compile_model(model, lr=1e-3, label_smoothing=0.1)
    model.summary()
    print("  Trainable params (phase 1): {:,}".format(
        sum(np.prod(v.shape) for v in model.trainable_variables)
    ))

    h1 = model.fit(
        train_ds,
        epochs=PHASE1_EPOCHS,
        validation_data=val_ds,
        class_weight=class_weight_dict,
        callbacks=[
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_accuracy', factor=0.5, patience=3, min_lr=1e-6, verbose=1
            ),
        ],
        verbose=1
    )
    print("\n  Phase 1 best val_acc: {:.4f}".format(max(h1.history['val_accuracy'])))

    # PHASE 2: Fine-tuning
    print("\n" + "=" * 60)
    print("  PHASE 2 -- Fine-tuning (unfreezing backbone from layer {})".format(UNFREEZE_FROM))
    print("=" * 60)

    backbone.trainable = True
    for layer in backbone.layers[:UNFREEZE_FROM]:
        layer.trainable = False

    n_trainable = sum(1 for l in backbone.layers if l.trainable)
    print("  Trainable backbone layers: {}/{}".format(n_trainable, len(backbone.layers)))
    print("  Total trainable params: {:,}".format(
        sum(np.prod(v.shape) for v in model.trainable_variables)
    ))

    compile_model(model, lr=2e-4, label_smoothing=0.05)

    h2 = model.fit(
        train_ds,
        epochs=PHASE2_EPOCHS,
        validation_data=val_ds,
        class_weight=class_weight_dict,
        callbacks=[
            tf.keras.callbacks.ModelCheckpoint(
                MODEL_SAVE_PATH, monitor='val_accuracy', mode='max',
                save_best_only=True, verbose=1
            ),
            tf.keras.callbacks.EarlyStopping(
                monitor='val_accuracy', mode='max', patience=12,
                restore_best_weights=True, verbose=1
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_accuracy', factor=0.5, patience=5,
                min_lr=5e-7, verbose=1
            ),
        ],
        verbose=1
    )

    best_val_acc = max(h2.history['val_accuracy'])
    print("\n  Phase 2 best val_accuracy: {:.4f}".format(best_val_acc))
    print("  Model saved to: {}".format(MODEL_SAVE_PATH))

    # Save combined history
    history_combined = {}
    for k, v1 in h1.history.items():
        history_combined[k] = [float(x) for x in v1] + [float(x) for x in h2.history.get(k, [])]
    with open(HISTORY_SAVE_PATH, 'w') as f:
        json.dump(history_combined, f, indent=2)
    print("  Training history saved to: {}".format(HISTORY_SAVE_PATH))

    # FINAL EVALUATION (test set, used exactly once)
    print("\n" + "=" * 60)
    print("  FINAL EVALUATION -- Loading best checkpoint")
    print("=" * 60)

    best_model = tf.keras.models.load_model(MODEL_SAVE_PATH)

    X_test_raw, y_test = load_test_data()
    print("  Preprocessing test set...")
    X_test = preprocess_batch(X_test_raw)

    print("  Running predictions on test set...")
    y_probs = best_model.predict(X_test, batch_size=BATCH_SIZE, verbose=1)
    y_pred  = np.argmax(y_probs, axis=1)

    acc          = accuracy_score(y_test, y_pred)
    f1_macro     = f1_score(y_test, y_pred, average='macro')
    f1_weighted  = f1_score(y_test, y_pred, average='weighted')
    prec_macro   = precision_score(y_test, y_pred, average='macro')
    rec_macro    = recall_score(y_test, y_pred, average='macro')

    print("\n" + "=" * 60)
    print("  TEST SET RESULTS -- emotion_model_v2.keras")
    print("=" * 60)
    print("  Overall Accuracy:  {:.4f}  ({:.2f}%)".format(acc, acc*100))
    print("  Macro F1:          {:.4f}".format(f1_macro))
    print("  Weighted F1:       {:.4f}".format(f1_weighted))
    print("  Macro Precision:   {:.4f}".format(prec_macro))
    print("  Macro Recall:      {:.4f}".format(rec_macro))
    print()
    print("  Per-class Report:")
    print(classification_report(y_test, y_pred, target_names=EMOTIONS))

    cm = confusion_matrix(y_test, y_pred)
    np.save(CM_SAVE_PATH, cm)
    print("  Confusion matrix saved to: {}".format(CM_SAVE_PATH))
    print("\n  Confusion Matrix (rows=true, cols=pred):")
    header = "{:12s}".format("") + "".join("{:>8s}".format(e[:4]) for e in EMOTIONS)
    print("  " + header)
    for i, row in enumerate(cm):
        row_str = "  {:12s}".format(EMOTIONS[i]) + "".join("{:8d}".format(v) for v in row)
        print(row_str)

    per_class_report = classification_report(
        y_test, y_pred, target_names=EMOTIONS, output_dict=True
    )
    elapsed = time.time() - start_time
    model_size_mb = os.path.getsize(MODEL_SAVE_PATH) / 1024 / 1024

    eval_report = {
        "model": "emotion_model_v2.keras",
        "backbone": "MobileNetV2 (ImageNet pretrained)",
        "input_shape": [IMG_SIZE, IMG_SIZE, 3],
        "test_accuracy": float(acc),
        "macro_f1": float(f1_macro),
        "weighted_f1": float(f1_weighted),
        "macro_precision": float(prec_macro),
        "macro_recall": float(rec_macro),
        "per_class": per_class_report,
        "confusion_matrix": cm.tolist(),
        "training_time_seconds": round(elapsed, 1),
        "model_size_mb": round(model_size_mb, 2),
        "val_accuracy_best": float(best_val_acc),
        "baseline_accuracy": 0.6172,
        "improvement_pp": round((acc - 0.6172) * 100, 2)
    }
    with open(REPORT_SAVE_PATH, 'w') as f:
        json.dump(eval_report, f, indent=2)
    print("\n  Full report saved to: {}".format(REPORT_SAVE_PATH))

    # Real-time compatibility
    import time as _time
    dummy = np.zeros((1, IMG_SIZE, IMG_SIZE, 3), dtype=np.float32)
    best_model.predict(dummy, verbose=0)
    t0 = _time.time()
    for _ in range(20):
        best_model.predict(dummy, verbose=0)
    avg_ms = (_time.time() - t0) / 20 * 1000

    print("\n" + "=" * 60)
    print("  REAL-TIME COMPATIBILITY")
    print("=" * 60)
    print("  Input shape:       {}x{}x3 RGB".format(IMG_SIZE, IMG_SIZE))
    print("  Model size:        {:.2f} MB".format(model_size_mb))
    print("  Avg inference:     {:.1f} ms/frame (CPU, single frame)".format(avg_ms))
    print("  Capture interval:  2000 ms (frontend)")
    print("  Real-time OK:      {}".format("YES" if avg_ms < 500 else "BORDERLINE"))
    print("  Total params:      {:,}".format(best_model.count_params()))

    print("\n" + "=" * 60)
    print("  FINAL SUMMARY")
    print("=" * 60)
    print("  Old model accuracy: 61.72%")
    print("  New model accuracy: {:.2f}%".format(acc*100))
    delta = (acc - 0.6172) * 100
    print("  Improvement:       {:+.2f} pp".format(delta))
    print("  85% target:        {}".format(
        "ACHIEVED" if acc >= 0.85 else "Not reached ({:.2f}%)".format(acc*100)
    ))
    print("  Training time:     {:.1f} min".format(elapsed/60))
    print("  Model size:        {:.2f} MB".format(model_size_mb))
    if acc > 0.6172:
        print("\n  New model OUTPERFORMS baseline.")
        print("  Waiting for approval before replacing production model.")
    else:
        print("\n  WARNING: New model does NOT outperform baseline. Keep old model.")
    print("=" * 60)


if __name__ == "__main__":
    main()
