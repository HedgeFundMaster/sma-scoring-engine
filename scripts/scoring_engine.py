import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import sys

# Configuration
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
DATA_PATH = Path(__file__).resolve().parent.parent / "outputs/quantitative_data_cleaned.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "outputs/quantitative_scores.csv"

def get_scoring_config():
    """Loads the scoring configuration from the YAML file."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)['quantitative_scoring']
    except FileNotFoundError:
        print(f"❌ Error: Configuration file not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, TypeError) as e:
        print(f"❌ Error: Invalid configuration format in {CONFIG_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

def validate_weights(config):
    """Validates that the metric weights sum to 100."""
    total_weight = sum(m['weight'] for m in config['metrics'].values())
    if total_weight != 100:
        print(f"⚠️ Warning: Metric weights sum to {total_weight}, not 100. Normalizing weights.", file=sys.stderr)
    return total_weight

def calculate_percentile_score(series, higher_is_better):
    """Calculates percentile rank, handling inversion for risk metrics."""
    numeric_series = pd.to_numeric(series, errors='coerce')
    if numeric_series.isnull().all():
        return pd.Series(0, index=numeric_series.index)

    if higher_is_better:
        return numeric_series.rank(pct=True).fillna(0) * 100
    else:
        return (1 - numeric_series.rank(pct=True, ascending=False)).fillna(0) * 100

def apply_penalties(df, penalties):
    """Applies penalties to scores based on specified thresholds."""
    for metric, config in penalties.items():
        if config.get('apply', False) and metric in df.columns:
            metric_series = pd.to_numeric(df[metric], errors='coerce')
            breach_condition = metric_series < config['threshold']
            df.loc[breach_condition, f"{metric}_Score"] -= config.get('penalty_points', 0)
    return df

def calculate_scores(df, config):
    """Calculates percentile scores for each metric."""
    for metric, params in config['metrics'].items():
        if metric in df.columns:
            df[f"{metric}_Score"] = calculate_percentile_score(df[metric], params['higher_is_better'])
    
    if 'penalties' in config:
        df = apply_penalties(df, config['penalties'])
        
    return df

def calculate_composite_score(df, config, total_weight):
    """Calculates the final composite quantitative score."""
    score_sum = pd.Series(0.0, index=df.index)
    for m, p in config['metrics'].items():
        score_col = f"{m}_Score"
        if score_col in df.columns:
            score_sum += df[score_col].fillna(0) * (p['weight'] / total_weight)
            
    df['Quantitative Score'] = score_sum
    return df

def main():
    """Main function to run the scoring engine."""
    try:
        print("Running quantitative scoring...")
        
        config = get_scoring_config()
        total_weight = validate_weights(config)
        
        if not DATA_PATH.exists():
            print(f"❌ Error: Cleaned quantitative data not found at {DATA_PATH}", file=sys.stderr)
            print("Please run the data_preprocessor.py script first.", file=sys.stderr)
            sys.exit(1)
            
        df = pd.read_csv(DATA_PATH)
        
        df_scored = calculate_scores(df, config)
        df_composite = calculate_composite_score(df_scored, config, total_weight)
        
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        output_cols = ['Fund Name', 'Quantitative Score'] + [f"{m}_Score" for m in config['metrics'] if f"{m}_Score" in df_composite.columns]
        df_composite[output_cols].to_csv(OUTPUT_PATH, index=False)
        
        print(f"✅ Quantitative scores saved to {OUTPUT_PATH}")

    except Exception as e:
        print(f"❌ Error in quantitative scoring engine: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
