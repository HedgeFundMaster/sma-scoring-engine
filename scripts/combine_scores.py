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
    
    df["Qualitative Score"].fillna(0, inplace=True)
    df["Quantitative Score"].fillna(0, inplace=True)
    
    df["Combined Score"] = (df["Qualitative Score"] * qual_weight) + (df["Quantitative Score"] * quant_weight)
    return df

def assign_tiers_and_explanation(df):
    """Assigns tiers and provides explanations based on the combined score."""
    tier1_cutoff = df["Combined Score"].quantile(0.75)
    tier2_cutoff = df["Combined Score"].quantile(0.50)
    
    def get_tier_explanation(score):
        if score >= tier1_cutoff:
            return "Tier 1", "This fund ranks in the top 25% of its peers, demonstrating exceptional overall performance."
        elif score >= tier2_cutoff:
            return "Tier 2", "This fund ranks in the top 50% of its peers, showing strong overall results."
        else:
            return "Tier 3", "This fund is in the bottom 50% of its peers, indicating opportunities for improvement."

    df[["Tier", "Justification"]] = df["Combined Score"].apply(lambda score: pd.Series(get_tier_explanation(score)))
    return df

def main():
    """Main function to combine qualitative and quantitative scores."""
    try:
        print("Combining scores...")
        
        config = get_combination_config()
        
        if not QUAL_SCORES_PATH.exists() or not QUANT_SCORES_PATH.exists():
            print(f"❌ Error: Score files not found. Please run the scoring engines first.", file=sys.stderr)
            sys.exit(1)

        df_qual = pd.read_csv(QUAL_SCORES_PATH)
        df_quant = pd.read_csv(QUANT_SCORES_PATH)
        
        df_merged = pd.merge(
            df_qual[['Fund Name', 'Qualitative Score']],
            df_quant[['Fund Name', 'Quantitative Score']],
            on="Fund Name",
            how="outer"
        )
        
        df_combined = calculate_combined_score(df_merged, config)
        df_final = assign_tiers_and_explanation(df_combined)
        
        COMBINED_SCORES_PATH.parent.mkdir(exist_ok=True)
        df_final.to_csv(COMBINED_SCORES_PATH, index=False)
        
        print(f"✅ Combined scores saved to {COMBINED_SCORES_PATH}")

    except Exception as e:
        print(f"❌ Error in combine_scores script: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
