import os
import numpy as np
from PIL import Image

def main():
    # 9. Make the script runnable from the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(script_dir, 'dataset')
    
    # 1. Read images from ml/emotion/dataset/train and ml/emotion/dataset/test
    train_dir = os.path.join(dataset_dir, 'train')
    test_dir = os.path.join(dataset_dir, 'test')
    
    # 8. Create output inside ml/emotion/dataset/processed
    output_dir = os.path.join(dataset_dir, 'processed')
    
    if not os.path.exists(train_dir) or not os.path.exists(test_dir):
        print(f"Error: Dataset directories not found at {train_dir} or {test_dir}")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Detect all 7 emotion classes
    emotions = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
    
    # 11. Validate that all 7 classes exist
    for split_dir, split_name in [(train_dir, 'train'), (test_dir, 'test')]:
        for em in emotions:
            em_dir = os.path.join(split_dir, em)
            if not os.path.exists(em_dir):
                print(f"Error: Missing class directory {em_dir} in {split_name} split.")
                return

    def process_split(split_dir, split_name):
        X, y = [], []
        print(f"Processing {split_name} data...")
        counts = {em: 0 for em in emotions}
        
        for class_idx, em in enumerate(emotions):
            em_dir = os.path.join(split_dir, em)
            for img_name in os.listdir(em_dir):
                if not img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                img_path = os.path.join(em_dir, img_name)
                
                # 3. Use 48x48 grayscale images
                img = Image.open(img_path).convert('L')
                img = img.resize((48, 48))
                
                # 4. Normalize pixel values (0-1 scaling prevents data leakage - Req 6)
                img_array = np.array(img, dtype=np.float32) / 255.0
                
                X.append(img_array)
                y.append(class_idx)
                counts[em] += 1
                
        # 10. Print the number of images found for every emotion class
        print(f"--- {split_name.upper()} ---")
        for em in emotions:
            print(f"  {em}: {counts[em]}")
        print(f"  Total: {sum(counts.values())}")
        
        X = np.array(X)
        y = np.array(y)
        
        # Save as numpy arrays
        np.save(os.path.join(output_dir, f'X_{split_name}.npy'), X)
        np.save(os.path.join(output_dir, f'y_{split_name}.npy'), y)
        print(f"Saved {split_name} arrays to {output_dir}\n")

    # 7. Preserve the existing train/test split
    # 5. Do not augment the test data (and train is only normalized)
    process_split(train_dir, 'train')
    process_split(test_dir, 'test')
    
    print("Preprocessing complete!")

if __name__ == "__main__":
    main()
