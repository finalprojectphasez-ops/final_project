import os
import cv2
import numpy as np
import json
import math

# Paths
base_dir = r"C:\Users\nisja\Downloads\MPIIGaze\MPIIGaze"
data_dir = os.path.join(base_dir, "Data", "Original")
out_dir = os.path.join("ml", "eye_contact", "dataset", "processed")
os.makedirs(out_dir, exist_ok=True)

# Participant split
train_participants = [f"p{i:02d}" for i in range(11)]  # p00 - p10
val_participants = [f"p{i:02d}" for i in range(11, 13)] # p11 - p12
test_participants = [f"p{i:02d}" for i in range(13, 15)] # p13 - p14

def get_split(p_id):
    if p_id in train_participants: return "train"
    if p_id in val_participants: return "val"
    if p_id in test_participants: return "test"
    return None

def calculate_gaze_angles(target_3d, eye_center_3d):
    """
    target_3d: (tx, ty, tz)
    eye_center_3d: (ex, ey, ez)
    Returns (pitch, yaw)
    """
    dx = target_3d[0] - eye_center_3d[0]
    dy = target_3d[1] - eye_center_3d[1]
    dz = target_3d[2] - eye_center_3d[2]
    
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    if length == 0:
        return 0.0, 0.0
        
    dx /= length
    dy /= length
    dz /= length
    
    pitch = math.asin(-dy)
    yaw = math.atan2(-dx, -dz)
    return pitch, yaw

def get_eye_crop(img, pts, target_size=(48, 36)):
    """ Crop eye based on 6 landmarks """
    pts = np.array(pts).reshape(-1, 2)
    xmin, ymin = np.min(pts, axis=0)
    xmax, ymax = np.max(pts, axis=0)
    
    w = xmax - xmin
    h = ymax - ymin
    
    # Add margin
    margin_w = int(w * 0.5)
    margin_h = int(h * 1.5)
    
    xmin = max(0, int(xmin - margin_w))
    xmax = min(img.shape[1], int(xmax + margin_w))
    ymin = max(0, int(ymin - margin_h))
    ymax = min(img.shape[0], int(ymax + margin_h))
    
    if xmin >= xmax or ymin >= ymax:
        return None
        
    crop = img[ymin:ymax, xmin:xmax]
    if crop.size == 0:
        return None
        
    crop = cv2.resize(crop, target_size)
    return crop

stats = {
    "total_valid": 0,
    "missing_images": 0,
    "malformed_rows": 0,
    "invalid_values": 0,
    "crop_failed": 0
}

X = {"train": [], "val": [], "test": []}
y = {"train": [], "val": [], "test": []}
head_pose = {"train": [], "val": [], "test": []}

sample_count = 0

print("Starting MPIIGaze preprocessing...")
for p_id in os.listdir(data_dir):
    p_dir = os.path.join(data_dir, p_id)
    if not os.path.isdir(p_dir): continue
    
    split = get_split(p_id)
    if not split: continue
    
    print(f"Processing {p_id} ({split})...")
    
    for day in os.listdir(p_dir):
        day_dir = os.path.join(p_dir, day)
        annot_file = os.path.join(day_dir, "annotation.txt")
        
        if not os.path.exists(annot_file): continue
        
        with open(annot_file, 'r') as f:
            lines = f.readlines()
            
        for idx, line in enumerate(lines):
            # Process every 4th frame to keep memory manageable (approx 100k samples)
            if idx % 4 != 0: continue
                
            line = line.strip()
            if not line: continue
            
            parts = line.split()
            if len(parts) != 41:
                stats["malformed_rows"] += 1
                continue
                
            try:
                vals = [float(x) for x in parts]
            except ValueError:
                stats["invalid_values"] += 1
                continue
                
            img_name = f"{(idx + 1):04d}.jpg"
            img_path = os.path.join(day_dir, img_name)
            
            if not os.path.exists(img_path):
                stats["missing_images"] += 1
                continue
                
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                stats["missing_images"] += 1
                continue
                
            # Parse columns
            right_eye_pts = vals[0:12]   # Image space left eye (Right Eye)
            left_eye_pts = vals[12:24]   # Image space right eye (Left Eye)
            target_3d = vals[26:29]      # 27-29 (0-indexed 26-28)
            h_pose = vals[29:35]         # 30-35 (0-indexed 29-34)
            right_eye_center = vals[35:38] # 36-38 (0-indexed 35-37)
            left_eye_center = vals[38:41]  # 39-41 (0-indexed 38-40)
            
            # Right Eye Sample
            right_crop = get_eye_crop(img, right_eye_pts)
            if right_crop is not None:
                pitch, yaw = calculate_gaze_angles(target_3d, right_eye_center)
                X[split].append(right_crop)
                y[split].append([pitch, yaw])
                head_pose[split].append(h_pose)
                stats["total_valid"] += 1
            else:
                stats["crop_failed"] += 1
                
            # Left Eye Sample
            left_crop = get_eye_crop(img, left_eye_pts)
            if left_crop is not None:
                pitch, yaw = calculate_gaze_angles(target_3d, left_eye_center)
                # Flip left eye horizontally to match right eye structure (common in gaze estimation)
                left_crop = cv2.flip(left_crop, 1)
                X[split].append(left_crop)
                y[split].append([pitch, -yaw]) # flip yaw for flipped image
                head_pose[split].append(h_pose)
                stats["total_valid"] += 1
            else:
                stats["crop_failed"] += 1

print("\nProcessing complete. Normalizing and saving...")

metadata = {
    "participants": {
        "train": train_participants,
        "val": val_participants,
        "test": test_participants
    },
    "input_shape": [36, 48, 1],
    "target_shape": [2],
    "target_features": ["pitch", "yaw"],
    "head_pose_shape": [6],
    "normalization": "pixel values divided by 255.0",
    "stats": stats
}

for split in ["train", "val", "test"]:
    if len(X[split]) == 0: continue
    
    # Convert to numpy and normalize
    X_arr = np.array(X[split], dtype=np.float32) / 255.0
    X_arr = np.expand_dims(X_arr, axis=-1) # Add channel dim
    
    y_arr = np.array(y[split], dtype=np.float32)
    hp_arr = np.array(head_pose[split], dtype=np.float32)
    
    np.save(os.path.join(out_dir, f"X_{split}.npy"), X_arr)
    np.save(os.path.join(out_dir, f"y_{split}.npy"), y_arr)
    np.save(os.path.join(out_dir, f"headpose_{split}.npy"), hp_arr)
    
    metadata[f"{split}_samples"] = len(X_arr)
    print(f"Saved {split}: X={X_arr.shape}, y={y_arr.shape}")

with open(os.path.join(out_dir, "metadata.json"), 'w') as f:
    json.dump(metadata, f, indent=4)

print("\n--- Summary ---")
for k, v in stats.items():
    print(f"{k}: {v}")
