import pandas as pd # type: ignore
import numpy as np # type: ignore
from pathlib import Path
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_scoring_config() -> Dict[str, Dict[str, Any]]:
    """
    Defines and returns the scoring configuration for SMA metrics.
    
    This configuration could be loaded from a file (e.g., YAML, JSON) in a future implementation.
    
    Returns:
        dict: A dictionary containing the configuration for each metric.
    """
    return {
        "Alpha (Since Inception)": {"weight": 0.05, "penalty": 0.15, "direction": "higher"},
        "Historical Sharpe Ratio (3Y)": {"weight": 0.10, "penalty": 0.10, "direction": "higher"},
        "Historical Sharpe Ratio (5Y)": {"weight": 0.05, "penalty": 0.10, "direction": "higher"},
        "Information Ratio (vs Category) (3Y)": {"weight": 0.10, "penalty": 0.10, "direction": "higher"},
        "Information Ratio (vs Category) (5Y)": {"weight": 0.05, "penalty": 0.10, "direction": "higher"},
        "Max Drawdown (3Y)": {"weight": 0.10, "penalty": 0.20, "direction": "lower"},
        "Max Drawdown (5Y)": {"weight": 0.05, "penalty": 0.20, "direction": "lower"},
        "Daily Value at Risk (VaR) 5% (3Y Lookback)": {"weight": 0.05, "penalty": 0.15, "direction": "lower"},
        "Daily Value at Risk (VaR) 5% (5Y Lookback)": {"weight": 0.05, "penalty": 0.15, "direction": "lower"},
        "Batting Average (3Y Lookback)": {"weight": 0.05, "penalty": 0.10, "direction": "higher"},
        "Batting Average (5Y Lookback)": {"weight": 0.05, "penalty": 0.10, "direction": "higher"},
        "Upside/Downside Ratio (3Y)": {"weight": 0.10, "penalty": 0.10, "direction": "higher"},
        "Upside/Downside Ratio (5Y)": {"weight": 0.05, "penalty": 0.10, "direction": "higher"},
    }

def validate_weights(metrics_info: Dict[str, Dict[str, Any]]) -> float:
    """
    Validate that weights are reasonable and log total weight.
    
    Args:
        metrics_info (dict): Dictionary containing metric configurations.
    
    Returns:
        float: Total weight sum.
    """
    total_weight = sum(cfg["weight"] for cfg in metrics_info.values())
    logger.info(f"Total weight sum: {total_weight:.4f}")
    
    if abs(total_weight - 1.0) > 0.01:  # Allow small tolerance
        logger.warning(f"Weights sum to {total_weight:.4f}, not 1.0")
    
    return total_weight

def load_data(file_path: Path) -> pd.DataFrame:
    """
    Load data from a CSV file.
    
    Args:
        file_path (Path): The path to the input CSV file.
        
    Returns:
        pd.DataFrame: The loaded and cleaned dataframe.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    logger.info(f"Loading data from: {file_path}")
    df = pd.read_csv(file_path, header=1)
    df.columns = df.columns.str.strip()
    logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
    return df

def compute_metric_score(df: pd.DataFrame, metric: str, cfg: Dict[str, Any]) -> pd.Series:
    """
    Compute a metric's score based on percentile ranking and apply penalties.

    This method is robust to outliers and handles missing data by assigning a
    penalized neutral score without affecting the scores of other entities.

    Args:
        df (pd.DataFrame): Input dataframe.
        metric (str): Name of the metric column.
        cfg (dict): Configuration for the metric, including direction and penalty.

    Returns:
        pd.Series: A series of scores between 0 and 1.
    """
    if metric not in df.columns:
        logger.warning(f"Column missing: {metric}. Assigning penalized neutral score.")
        return pd.Series(0.5 * (1 - cfg["penalty"]), index=df.index)

    scores = pd.Series(np.nan, index=df.index)
    valid_mask = df[metric].notna()
    
    # Calculate scores only for valid (non-missing) data
    if valid_mask.any():
        # Percentile ranking is robust to outliers
        ranked_scores = df.loc[valid_mask, metric].rank(pct=True)
        
        if cfg["direction"] == "lower":
            # For metrics where lower is better, invert the rank
            scores.loc[valid_mask] = 1 - ranked_scores
        else:
            scores.loc[valid_mask] = ranked_scores

    # Apply a consistent penalty for missing data based on a neutral 0.5 score
    missing_mask = ~valid_mask
    if missing_mask.any():
        penalty_score = 0.5 * (1 - cfg["penalty"])
        scores.loc[missing_mask] = penalty_score
        logger.info(f"Assigned penalized score of {penalty_score:.2f} to {missing_mask.sum()} missing values in '{metric}'")

    return scores

def calculate_scores(df: pd.DataFrame, metrics_info: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    """
    Calculate scores for all metrics.
    
    Args:
        df (pd.DataFrame): The input dataframe.
        metrics_info (dict): The scoring configuration.
        
    Returns:
        pd.DataFrame: Dataframe with added score columns.
    """
    df_scored = df.copy()
    for metric, cfg in metrics_info.items():
        df_scored[f"{metric}_score"] = compute_metric_score(df_scored, metric, cfg)
    return df_scored

def calculate_composite_score(df: pd.DataFrame, metrics_info: Dict[str, Dict[str, Any]], total_weight: float) -> pd.DataFrame:
    """
    Calculate the composite quantitative score.
    
    Args:
        df (pd.DataFrame): The dataframe with individual scores.
        metrics_info (dict): The scoring configuration.
        total_weight (float): The sum of all metric weights.
        
    Returns:
        pd.DataFrame: Dataframe with the "Quantitative Score" column.
    """
    logger.info("Computing weighted composite quantitative score")
    score_cols = [f"{m}_score" for m in metrics_info.keys() if f"{m}_score" in df.columns]
    weights = np.array([metrics_info[m.replace('_score', '')]["weight"] for m in score_cols])
    
    df["Quantitative Score"] = (df[score_cols] @ weights / total_weight) * 100
    return df

def assign_tier(score: float) -> str:
    """
    Assign tier based on quantitative score.
    
    Args:
        score (float): Quantitative score (0-100).
    
    Returns:
        str: Tier assignment.
    """
    if score >= 85:
        return "Top Pick"
    elif score >= 70:
        return "Consider"
    elif score >= 50:
        return "Watch List"
    return "Do Not Recommend"

def apply_tier_logic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply tiering logic to the dataframe.
    
    Args:
        df (pd.DataFrame): The dataframe with quantitative scores.
        
    Returns:
        pd.DataFrame: Dataframe with the "Tier" column.
    """
    df["Tier"] = df["Quantitative Score"].apply(assign_tier)
    tier_counts = df["Tier"].value_counts()
    logger.info(f"Tier distribution: {tier_counts.to_dict()}")
    return df

def save_results(df: pd.DataFrame, file_path: Path):
    """
    Save the scored dataframe to a CSV file.
    
    Args:
        df (pd.DataFrame): The final scored dataframe.
        file_path (Path): The path to the output CSV file.
    """
    file_path.parent.mkdir(exist_ok=True)
    logger.info(f"Saving results to: {file_path}")
    df.to_csv(file_path, index=False)

def main():
    """
    Main function to execute the SMA scoring system.
    
    This system evaluates SMA strategies based on multiple quantitative metrics,
    applies weighted scoring with penalties for missing data, and assigns tiers
    based on the composite quantitative score.
    """
    # === Configuration ===
    input_path = Path("data/sma_data_structured.csv")
    output_path = Path("outputs/sma_scored.csv")
    metrics_info = get_scoring_config()
    
    # === Execution Pipeline ===
    total_weight = validate_weights(metrics_info)
    df = load_data(input_path)
    df_scored = calculate_scores(df, metrics_info)
    df_composite = calculate_composite_score(df_scored, metrics_info, total_weight)
    df_tiered = apply_tier_logic(df_composite)
    
    save_results(df_tiered, output_path)
    
    # === Reporting ===
    score_stats = df_tiered["Quantitative Score"].describe()
    logger.info(f"Score statistics: Mean={score_stats['mean']:.2f}, Std={score_stats['std']:.2f}, Min={score_stats['min']:.2f}, Max={score_stats['max']:.2f}")
    
    print("\n✅ Sample Scored SMA Strategies:\n")
    print(df_scored.head().to_string(index=False))
    logger.info("SMA scoring completed successfully.")

if __name__ == "__main__":
    main()
