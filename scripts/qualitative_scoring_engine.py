import pandas as pd
import yaml
from pathlib import Path
import sys

# --- Configuration ---
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
DATA_PATH = Path(__file__).resolve().parent.parent / "data/Qualitative Scoring.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "outputs/qualitative_scores.csv"

def get_qualitative_config():
    """Loads the qualitative scoring configuration from the YAML file."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)["qualitative_scoring"]

def calculate_final_score(df, config):
    """Calculates the final qualitative score based on weighted category scores."""
    weights = config["weights"]
    score_mapping = config["score_mapping"]
    
    # Convert categorical string columns to numerical scores
    for col in weights.keys():
        if col in df.columns:
            # Replace known values and fill any unmapped values with 0
            df[f"{col}_Score"] = df[col].replace(score_mapping).apply(pd.to_numeric, errors='coerce').fillna(0)

    # Calculate the weighted average score
    total_weight = sum(weights.values())
    df["Qualitative Score"] = sum(df[f"{cat}_Score"] * weight for cat, weight in weights.items()) / total_weight
    
    return df

def main():
    """Main function to run the qualitative scoring engine."""
    try:
        print("Running qualitative scoring...")
        
        config = get_qualitative_config()
        
        df = pd.read_csv(DATA_PATH)
        
        # Calculate the final score
        df_scored = calculate_final_score(df, config)
        
        # Save the results
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        df_scored.to_csv(OUTPUT_PATH, index=False)
        
        print(f"Qualitative scores saved to {OUTPUT_PATH}")

    except Exception as e:
        print(f"Error in qualitative scoring engine: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()