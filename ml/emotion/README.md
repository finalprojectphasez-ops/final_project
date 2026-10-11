# Facial Emotion Detection Pipeline (FER-2013)

This directory contains the ML pipeline for training a Convolutional Neural Network (CNN) to detect 7 facial emotions using the FER-2013 dataset.

**Classes**: angry, disgust, fear, happy, sad, surprise, neutral

> **NOTE:** Training deep learning models takes significant computational power. It is highly recommended to run this pipeline in **Google Colab** with a GPU instead of your local machine.

## Prerequisites
1. You will need a Kaggle account to download the FER-2013 dataset.
2. In Colab (or locally), install the requirements:
   ```bash
   pip install -r requirements.txt
   ```

## Dataset: FER-2013
We use the original FER-2013 dataset from Kaggle.

1. Go to: https://www.kaggle.com/c/challenges-in-representation-learning-facial-expression-recognition-challenge/data
2. Download `fer2013.tar.gz` (or use the Kaggle API).
3. Extract `fer2013.csv` and place it in a `data/` folder inside this `emotion/` directory.

Directory structure before preprocessing:
```text
ml/emotion/
├── data/
│   └── fer2013.csv
├── preprocess.py
├── train.py
...
```

## Step 1: Preprocessing
The preprocessing script reads the `fer2013.csv` file, converts the pixel data into 48x48 images, and splits it into train/validation/test directories.

Run:
```bash
python preprocess.py
```
This will create a `dataset/` folder containing `train`, `val`, and `test` subdirectories.

## Step 2: Training
The training script loads the images from the `dataset/train` and `dataset/val` folders, applies data augmentation to the training set, and trains a CNN model.

Run:
```bash
python train.py
```
During training, the best model will be saved as `emotion_model.keras`.
The script will also generate a `training_history.png` chart.

## Step 3: Evaluation
After training, evaluate the model on the unseen test dataset.

Run:
```bash
python evaluate.py
```
This will print accuracy, precision, recall, and F1 score, and save a `confusion_matrix.png` image.

## Step 4: Backend Integration
Once you are satisfied with the model:
1. Download `emotion_model.keras` from Google Colab.
2. Place it in the backend directory: `backend/ml_models/emotion_model.keras`.
3. Restart your FastAPI backend server.
