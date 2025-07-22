import pandas as pd
import yaml
from pathlib import Path
import sys

# --- Configuration ---
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
QUAL_SCORES_PATH = Path(__file__).resolve().parent.parent / "outputs/qualitative_scores.csv"
QUANT_SCORES_PATH = Path(__file__).resolve().parent.parent / "outputs/quantitative_scores.csv"
COMBINED_SCORES_PATH = Path(__file__).resolve().parent.parent / "outputs/combined_scores.csv"

def get_combination__config():
    """Loads the combination configuration from the YAML file."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)["combination_config"]
    except FileNotFoundError:
        print(f"❌ Error: Configuration file not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, TypeError) as e:
        print(f"❌ Error: Invalid configuration format in {CONFIG_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

def calculate_combined_score(df, config):
    """Calculates the final combined score based on weighted inputs."""
    qual_weight = config.get("qualitative_weight", 0.4)
    quant_weight = config.get("quantitative_weight", 0.6)
    
    # Fill missing scores with 0 before calculating the combined score
    df["Qualitative Score"].fillna(0, inplace=True)
    df["Quantitative Score"].fillna(0, inplace=True)
    
    df["Combined Score"] = (df["Qualitative Score"] * qual_weight) + (df["Quantitative Score"] * quant_weight)
    return df

def main():
    """Main function to combine qualitative and quantitative scores."""
    try:
        print("Combining scores...")
        
        config = get_combination_config()
        
        # Read the score files
        try:
            df_qual = pd.read_csv(QUAL_SCORES_PATH)
            df_quant = pd.read_csv(QUANT_SCORES_PATH)
        except FileNotFoundError as e:
            print(f"❌ Error: Score file not found: {e.filename}", file=sys.stderr)
            print("Please run the scoring engines first.", file=sys.stderr)
            sys.exit(1)
        
        # Use an outer merge to keep all funds from both files
        df_merged = pd.merge(
            df_qual[['Fund Name', 'Qualitative Score']],
            df_quant[['Fund Name', 'Quantitative Score']],
            on="Fund Name",
            how="outer"  # Keep all funds
        )
        
        df_combined = calculate_combined_score(df_merged, config)
        
        # Save the combined scores
        COMBINED_SCORES_PATH.parent.mkdir(exist_ok=True)
        df_combined.to_csv(COMBINED_SCORES_PATH, index=False)
        
        print(f"✅ Combined scores saved to {COMBINED_SCORES_PATH}")

    except Exception as e:
        print(f"❌ Error in combine_scores script: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
