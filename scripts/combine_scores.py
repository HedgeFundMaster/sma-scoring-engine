import pandas as pd
import yaml
from pathlib import Path
import sys

# --- Configuration ---
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
QUAL_SCORES_PATH = Path(__file__).resolve().parent.parent / "outputs/qualitative_scores.csv"
QUANT_SCORES_PATH = Path(__file__).resolve().parent.parent / "outputs/quantitative_scores.csv"
COMBINED_SCORES_PATH = Path(__file__).resolve().parent.parent / "outputs/combined_scores.csv"

def get_combination_config():
    """Loads the combination configuration from the YAML file."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)["combination_config"]

def calculate_combined_score(df, config):
    """Calculates the final combined score based on weighted inputs."""
    qual_weight = config["qualitative_weight"]
    quant_weight = config["quantitative_weight"]
    
    df["Combined Score"] = (df["Qualitative Score"] * qual_weight) + (df["Quantitative Score"] * quant_weight)
    return df

def main():
    """Main function to combine qualitative and quantitative scores."""
    try:
        print("Combining scores...")
        
        config = get_combination_config()
        
        df_qual = pd.read_csv(QUAL_SCORES_PATH)
        df_quant = pd.read_csv(QUANT_SCORES_PATH)
        
        df_qual.rename(columns={"Name": "Fund Name"}, inplace=True)
        df_quant.rename(columns={"Name": "Fund Name"}, inplace=True)
        
        df_merged = pd.merge(
            df_qual[["Fund Name", "Qualitative Score"]],
            df_quant[["Fund Name", "Quantitative Score"]],
            on="Fund Name",
            how="inner"
        )
        
        df_combined = calculate_combined_score(df_merged, config)
        
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        df_combined.to_csv(COMBINED_SCORES_PATH, index=False)
        
        print(f"Combined scores saved to {COMBINED_SCORES_PATH}")

    except Exception as e:
        print(f"Error in combine_scores script: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()