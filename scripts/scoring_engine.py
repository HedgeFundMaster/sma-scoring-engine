import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import sys

# Configuration
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
DATA_PATH = Path(__file__).resolve().parent.parent / "data/sma_data_structured.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "outputs/quantitative_scores.csv"

def get_scoring_config():
    """Loads the scoring configuration from the YAML file."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)['quantitative_scoring']

def validate_weights(config):
    """Validates that the metric weights sum to 100."""
    total_weight = sum(m['weight'] for m in config['metrics'].values())
    if total_weight != 100:
        raise ValueError(f"Metric weights must sum to 100, but got {total_weight}")
    return total_weight

def calculate_percentile_score(series, higher_is_better):
    """Calculates percentile rank, handling inversion for risk metrics."""
    if higher_is_better:
        return series.rank(pct=True) * 100
    else:
        return (1 - series.rank(pct=True)) * 100

def apply_penalties(df, penalties):
    """Applies penalties to scores based on specified thresholds."""
    for metric, config in penalties.items():
        if config['apply'] and metric in df.columns:
            breach_condition = df[metric] < config['threshold']
            df.loc[breach_condition, f"{metric}_Score"] -= config['penalty_points']
    return df

def calculate_scores(df, config):
    """Calculates percentile scores for each metric."""
    for metric, params in config['metrics'].items():
        if metric in df.columns:
            # Clean data: convert to numeric and fill missing values with the median
            numeric_series = pd.to_numeric(df[metric], errors='coerce')
            numeric_series.fillna(numeric_series.median(), inplace=True)
            df[f"{metric}_Score"] = calculate_percentile_score(numeric_series, params['higher_is_better'])
    
    if 'penalties' in config:
        df = apply_penalties(df, config['penalties'])
        
    return df

def calculate_composite_score(df, config, total_weight):
    """Calculates the final composite quantitative score."""
    score_sum = pd.Series(0, index=df.index)
    for m, p in config['metrics'].items():
        score_col = f"{m}_Score"
        if score_col in df.columns:
            score_sum += df[score_col].fillna(0) * (p['weight'] / total_weight)
            
    df['Quantitative Score'] = score_sum
    return df

def apply_tier_logic(df):
    """Placeholder for tier logic."""
    return df

def main():
    """Main function to run the scoring engine."""
    try:
        print("Running quantitative scoring...")
        
        config = get_scoring_config()
        total_weight = validate_weights(config)
        
        df = pd.read_csv(DATA_PATH)
        
        df_scored = calculate_scores(df, config)
        df_composite = calculate_composite_score(df_scored, config, total_weight)
        df_final = apply_tier_logic(df_composite)
        
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        df_final.to_csv(OUTPUT_PATH, index=False)
        
        print(f"Quantitative scores saved to {OUTPUT_PATH}")

    except Exception as e:
        print(f"Error in quantitative scoring engine: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()