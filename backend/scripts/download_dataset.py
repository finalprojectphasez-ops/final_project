import os
import zipfile
import sys
from pathlib import Path

def download_dataset():
    dataset_name = "snehaanbhawal/resume-dataset"
    backend_dir = Path(__file__).parent.parent
    data_dir = backend_dir / "data" / "resume_dataset"
    
    # Create target directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"Target directory: {data_dir}")
    print(f"Attempting to download dataset: {dataset_name}...")
    
    try:
        # Import kaggle here so the script can fail gracefully if not authenticated
        import kaggle
    except OSError as e:
        if "Could not find kaggle.json" in str(e):
            print("\n[ERROR]: Kaggle authentication required.")
            print("To proceed, you must provide Kaggle credentials:")
            print("1. Log in to https://www.kaggle.com/")
            print("2. Go to your Account Settings and click 'Create New Token'")
            print("3. Save the downloaded 'kaggle.json' file to:")
            print("   C:\\Users\\<YourUsername>\\.kaggle\\kaggle.json (on Windows)")
            print("4. Re-run this script once the file is in place.\n")
            sys.exit(1)
        else:
            raise
    except Exception as e:
        print(f"Error initializing Kaggle API: {e}")
        sys.exit(1)

    try:
        kaggle.api.authenticate()
        print("Successfully authenticated with Kaggle API.")
        
        # Download files
        kaggle.api.dataset_download_files(
            dataset_name, 
            path=str(data_dir), 
            unzip=True
        )
        print("\n[SUCCESS] Dataset successfully downloaded and extracted.")
        
        # List extracted files
        print("\nExtracted files:")
        for file in os.listdir(data_dir):
            print(f"- {file}")
            
    except Exception as e:
        print(f"\n[ERROR] Error downloading dataset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_dataset()
