import pandas as pd
import yaml
from pathlib import Path
import sys

# --- Configuration ---
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
DATA_PATH = Path(__file__).resolve().parent.parent / "outputs/qualitative_data_cleaned.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "outputs/qualitative_scores.csv"

def get_qualitative_config():
    """Loads the qualitative scoring configuration from the YAML file."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)["qualitative_scoring"]
    except FileNotFoundError:
        print(f"❌ Error: Configuration file not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, TypeError) as e:
        print(f"❌ Error: Invalid configuration format in {CONFIG_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

def calculate_final_score(df, config):
    """Calculates the final qualitative score based on weighted category scores."""
    weights = config.get("weights", {})
    score_mapping = config.get("score_mapping", {})
    
    if not weights or not score_mapping:
        print("❌ Error: 'weights' or 'score_mapping' is missing in the qualitative config.", file=sys.stderr)
        sys.exit(1)

    total_score = pd.Series(0.0, index=df.index)
    total_weight = 0.0

    for col, weight in weights.items():
        if col in df.columns:
            score_col = f"{col}_Score"
            df[score_col] = df[col].map(score_mapping).fillna(0)
            total_score += df[score_col] * weight
            total_weight += weight

    if total_weight == 0:
        df["Qualitative Score"] = 0
    else:
        df["Qualitative Score"] = total_score / total_weight
    
    return df

def main():
    """Main function to run the qualitative scoring engine."""
    try:
        print("Running qualitative scoring...")
        
        config = get_qualitative_config()
        
        if not DATA_PATH.exists():
            print(f"❌ Error: Cleaned qualitative data not found at {DATA_PATH}", file=sys.stderr)
            print("Please run the data_preprocessor.py script first.", file=sys.stderr)
            sys.exit(1)
            
        df = pd.read_csv(DATA_PATH)
        
        df_scored = calculate_final_score(df, config)
        
        output_cols = ['Fund Name', 'Qualitative Score', 'Manager Tenure (Years)']
        score_cols = [f"{cat}_Score" for cat in config.get("weights", {}).keys() if f"{cat}_Score" in df_scored.columns]
        output_cols.extend(score_cols)
        
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        df_scored[output_cols].to_csv(OUTPUT_PATH, index=False)
        
        print(f"✅ Qualitative scores saved to {OUTPUT_PATH}")

    except Exception as e:
        print(f"❌ Error in qualitative scoring engine: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
