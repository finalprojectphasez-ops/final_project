import os
import argparse
from datasets import load_dataset, Audio, DatasetDict

def prepare(pilot=False):
    print("Loading dataset: ishands/commonvoice-indian_accent")
    try:
        dataset = load_dataset("ishands/commonvoice-indian_accent", split="train", trust_remote_code=True)
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    if pilot:
        print("Pilot mode: selecting 100 samples for training, 20 for validation")
        dataset = dataset.shuffle(seed=42)
        train_ds = dataset.select(range(100))
        val_ds = dataset.select(range(100, 120))
        test_ds = dataset.select(range(120, 140))
        
        ds_dict = DatasetDict({
            "train": train_ds,
            "validation": val_ds,
            "test": test_ds
        })
    else:
        print("Preparing full dataset splits...")
        train_test = dataset.train_test_split(test_size=0.2, seed=42)
        val_test = train_test['test'].train_test_split(test_size=0.5, seed=42)
        ds_dict = DatasetDict({
            "train": train_test['train'],
            "validation": val_test['train'],
            "test": val_test['test']
        })

    print("Resampling audio to 16000Hz...")
    ds_dict = ds_dict.cast_column("audio", Audio(sampling_rate=16000))
    
    # Check for missing transcripts
    print("Checking for missing transcripts...")
    def filter_empty(example):
        return example["sentence"] is not None and len(example["sentence"].strip()) > 0
    ds_dict = ds_dict.filter(filter_empty)

    output_dir = os.path.join(os.path.dirname(__file__), "processed_data_pilot" if pilot else "processed_data")
    print(f"Saving prepared dataset to {output_dir}")
    ds_dict.save_to_disk(output_dir)
    print("Dataset preparation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true", help="Prepare a small pilot dataset")
    args = parser.parse_args()
    prepare(pilot=args.pilot)
