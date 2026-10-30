"""Load and parse Bitext customer support dataset."""
import pandas as pd
from pathlib import Path


def load_dataset(csv_path):
    """Load Bitext dataset from CSV file.
    
    Columns: flags, instruction, category, intent, response
    """
    df = pd.read_csv(csv_path)
    return df


def load_train_validation():
    """Load both train and validation datasets."""
    train_df = load_dataset("data/train.csv")
    validation_df = load_dataset("data/validation.csv")
    
    print(f"Train set: {len(train_df)} samples")
    print(f"Validation set: {len(validation_df)} samples")
    print(f"Columns: {list(train_df.columns)}")
    print(f"Intents: {train_df['intent'].nunique()}")
    print(f"Categories: {train_df['category'].nunique()}")
    
    return train_df, validation_df


def get_intent_distribution(df):
    """Get distribution of intents in dataset."""
    return df['intent'].value_counts()


def get_category_distribution(df):
    """Get distribution of categories in dataset."""
    return df['category'].value_counts()
