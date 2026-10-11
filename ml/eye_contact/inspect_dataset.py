import os

base_dir = r"C:\Users\nisja\Downloads\MPIIGaze\MPIIGaze"
annotation_dir = os.path.join(base_dir, "Annotation Subset")
data_dir = os.path.join(base_dir, "Data", "Original")

total_annotations = 0
total_valid = 0
total_missing = 0
total_malformed = 0
coords_per_row = None
format_consistent = True
example_row = None

print(f"Exact dataset path detected: {base_dir}")

print(f"\n{'Participant':<15} | {'Annotation rows':<15} | {'Valid':<10} | {'Invalid':<10}")
print("-" * 55)

for i in range(15):
    p_id = f"p{i:02d}"
    annot_file = os.path.join(annotation_dir, f"{p_id}.txt")
    
    if not os.path.exists(annot_file):
        continue
        
    p_total = 0
    p_valid = 0
    p_missing = 0
    
    with open(annot_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            parts = line.split()
            if len(parts) < 2:
                total_malformed += 1
                continue
                
            img_path = parts[0]
            numeric_values = parts[1:]
            
            if coords_per_row is None:
                coords_per_row = len(numeric_values)
                example_row = line
            elif coords_per_row != len(numeric_values):
                format_consistent = False
                
            p_total += 1
            total_annotations += 1
            
            full_img_path = os.path.join(data_dir, p_id, img_path)
            if os.path.exists(full_img_path):
                p_valid += 1
                total_valid += 1
            else:
                p_missing += 1
                total_missing += 1
                
    print(f"{p_id:<15} | {p_total:<15} | {p_valid:<10} | {p_missing:<10}")

print("\n--- Summary ---")
print(f"Total annotations: {total_annotations}")
print(f"Total valid annotations: {total_valid}")
print(f"Total missing images: {total_missing}")
print(f"Total malformed rows: {total_malformed}")
print(f"Number of numeric values after image path: {coords_per_row}")
print(f"Is format consistent across all files?: {format_consistent}")
print(f"Example row:\n{example_row}")

print("\n--- Analysis of Annotations ---")
print("Are gaze labels directly available?")
print("Based on the ReadMe.txt, the Annotation Subset contains:")
print(" - '12 facial landmarks, face bounding box, two eye bounding boxes, and pupil position' (ReadMe Line 31)")
print(" - '6 facial landmarks (four eye corners, two mouth corners) and (x,y) position of two pupil centers' (ReadMe Line 95)")
print(f"The number of numeric values found per row is {coords_per_row}. If this is 16, it matches exactly 8 (x,y) pairs (6 landmarks + 2 pupils).")
print("The annotation files do NOT contain direct gaze targets/directions (3D vectors or 2D angles).")
print("The gaze target values (dimension 25-26, 27-29) are ONLY found in the 'annotation.txt' files within the Data/Original directories.")
print("For the next preprocessing step, if we want to train a gaze estimator, we must parse the 'annotation.txt' files inside 'Data/Original' instead of these 'Annotation Subset' files, as the 'Annotation Subset' lacks gaze direction labels.")
