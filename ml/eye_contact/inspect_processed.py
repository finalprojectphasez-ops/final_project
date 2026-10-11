import os
import numpy as np
import json

out_dir = os.path.join("ml", "eye_contact", "dataset", "processed")
meta_path = os.path.join(out_dir, "metadata.json")

if not os.path.exists(meta_path):
    print(f"Error: {meta_path} not found.")
    exit(1)

with open(meta_path, 'r') as f:
    metadata = json.load(f)

print("--- Data Split ---")
train_p = set(metadata["participants"]["train"])
val_p = set(metadata["participants"]["val"])
test_p = set(metadata["participants"]["test"])

print(f"Train participants: {sorted(list(train_p))}")
print(f"Val participants: {sorted(list(val_p))}")
print(f"Test participants: {sorted(list(test_p))}")

print("\n--- Verifying Overlaps ---")
t_v_overlap = train_p.intersection(val_p)
t_t_overlap = train_p.intersection(test_p)
v_t_overlap = val_p.intersection(test_p)

print(f"TRAIN AND VALIDATION OVERLAP = empty? {len(t_v_overlap) == 0}")
print(f"TRAIN AND TEST OVERLAP = empty? {len(t_t_overlap) == 0}")
print(f"VALIDATION AND TEST OVERLAP = empty? {len(v_t_overlap) == 0}")

print("\n--- Processed Dataset Stats ---")
for split in ["train", "val", "test"]:
    x_path = os.path.join(out_dir, f"X_{split}.npy")
    y_path = os.path.join(out_dir, f"y_{split}.npy")
    if os.path.exists(x_path):
        X = np.load(x_path)
        y = np.load(y_path)
        print(f"[{split.upper()}] Samples: {X.shape[0]}, Input Shape: {X.shape[1:]}, Target Shape: {y.shape[1:]}")
        print(f"          Target min/max: min=[{y[:,0].min():.3f}, {y[:,1].min():.3f}], max=[{y[:,0].max():.3f}, {y[:,1].max():.3f}]")

print("\n--- Removal Stats ---")
stats = metadata["stats"]
print(f"Total valid samples collected: {stats['total_valid']}")
print(f"Removed - missing images: {stats['missing_images']}")
print(f"Removed - malformed rows: {stats['malformed_rows']}")
print(f"Removed - invalid values: {stats['invalid_values']}")
print(f"Removed - crop failed: {stats['crop_failed']}")
