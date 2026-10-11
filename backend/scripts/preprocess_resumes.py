import os
import re
import json
import pandas as pd
from pathlib import Path

def clean_resume_text(text):
    if not isinstance(text, str):
        return ""
    # Remove excessive newlines and spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove weird artifacts or encoded characters
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return text.strip()

def preprocess():
    backend_dir = Path(__file__).parent.parent
    data_dir = backend_dir / "data" / "resume_dataset"
    csv_path = data_dir / "Resume.csv"
    output_path = data_dir / "cleaned_resumes.json"
    
    if not csv_path.exists():
        print(f"❌ Could not find {csv_path}")
        print("Make sure you run download_dataset.py first!")
        return

    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # We want to map Kaggle categories to our predefined roles
    # The categories in this dataset are usually broad, e.g. "INFORMATION-TECHNOLOGY", "DATA-SCIENCE"
    role_mapping = {
        "DATA-SCIENCE": ["ML Engineer", "Data Analyst"],
        "INFORMATION-TECHNOLOGY": ["Full Stack Engineer", "Frontend Developer", "Backend Engineer", "DevOps / SRE"],
        "ENGINEERING": ["Full Stack Engineer", "Backend Engineer"]
    }

    # Normalize category names
    if "Category" in df.columns:
        category_col = "Category"
    else:
        # Fallback if the column is named differently
        category_col = [c for c in df.columns if "cat" in c.lower() or "label" in c.lower()][0]

    # Pre-process
    print("Cleaning text and mapping categories...")
    processed_data = {
        "Full Stack Engineer": [],
        "Frontend Developer": [],
        "Backend Engineer": [],
        "DevOps / SRE": [],
        "ML Engineer": [],
        "Data Analyst": []
    }
    
    count = 0
    for _, row in df.iterrows():
        cat = str(row.get(category_col, "")).upper().strip()
        text = str(row.get("Resume_str", ""))
        if not text:
            continue
            
        cleaned = clean_resume_text(text)
        if len(cleaned) < 100:
            continue  # Skip junk
            
        # Map to our roles
        target_roles = role_mapping.get(cat, [])
        for role in target_roles:
            processed_data[role].append(cleaned)
            count += 1

    # Save to JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed_data, f)
        
    print(f"✅ Preprocessing complete! Saved {count} mapped resumes to {output_path}")
    
    # Print stats
    print("\nStats per role:")
    for role, resumes in processed_data.items():
        print(f"- {role}: {len(resumes)} resumes")

if __name__ == "__main__":
    preprocess()
