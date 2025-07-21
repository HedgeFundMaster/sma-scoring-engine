import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Tuple
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_combination_config() -> Dict[str, float]:
    """
    Defines the weights for combining qualitative and quantitative scores.
    
    Returns:
        dict: A dictionary with weights for each score type.
    """
    return {
        "quantitative_weight": 0.6,
        "qualitative_weight": 0.4
    }

def load_data(qual_path: Path, quant_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads the qualitative and quantitative scored data.
    
    Args:
        qual_path (Path): Path to the qualitative scores CSV.
        quant_path (Path): Path to the quantitative scores CSV.
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: A tuple of dataframes for qualitative and quantitative scores.
    """
    if not qual_path.exists():
        raise FileNotFoundError(f"Qualitative scores file not found: {qual_path}")
    if not quant_path.exists():
        raise FileNotFoundError(f"Quantitative scores file not found: {quant_path}")
        
    logger.info(f"Loading qualitative scores from {qual_path}")
    df_qual = pd.read_csv(qual_path)
    
    logger.info(f"Loading quantitative scores from {quant_path}")
    df_quant = pd.read_csv(quant_path)
    
    # Standardize column name for merging
    df_quant.rename(columns={"Name": "Fund Name"}, inplace=True)
    
    return df_qual, df_quant

def merge_scores(df_qual: pd.DataFrame, df_quant: pd.DataFrame) -> pd.DataFrame:
    """
    Merges qualitative and quantitative dataframes on 'Fund Name'.
    
    Args:
        df_qual (pd.DataFrame): Dataframe with qualitative scores.
        df_quant (pd.DataFrame): Dataframe with quantitative scores.
        
    Returns:
        pd.DataFrame: A merged dataframe with scores from both sources.
    """
    logger.info("Merging qualitative and quantitative scores.")
    # Select key columns to avoid clutter
    qual_cols = ["Fund Name", "Qualitative Score"]
    quant_cols = ["Fund Name", "Quantitative Score", "Tier"]
    
    df_merged = pd.merge(df_quant[quant_cols], df_qual[qual_cols], on="Fund Name", how="inner")
    
    missing_count = len(df_quant) - len(df_merged)
    if missing_count > 0:
        logger.warning(f"{missing_count} funds from the quantitative set were not found in the qualitative set and were dropped.")
        
    return df_merged

def calculate_combined_score(df: pd.DataFrame, config: Dict[str, float]) -> pd.DataFrame:
    """
    Calculates the final combined score based on configured weights.
    
    Args:
        df (pd.DataFrame): The merged dataframe.
        config (dict): Dictionary containing the weights.
        
    Returns:
        pd.DataFrame: Dataframe with the 'Combined Score' column.
    """
    logger.info("Calculating combined score.")
    df["Combined Score"] = (
        df["Quantitative Score"] * config["quantitative_weight"] +
        df["Qualitative Score"] * config["qualitative_weight"]
    )
    return df

def assign_quadrant(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns a quadrant based on whether scores are above or below the median.
    
    This provides a clear, strategic overview of each fund's profile.
    
    Args:
        df (pd.DataFrame): The dataframe with combined scores.
        
    Returns:
        pd.DataFrame: Dataframe with the 'Quadrant' column.
    """
    logger.info("Assigning strategic quadrants.")
    qual_median = df["Qualitative Score"].median()
    quant_median = df["Quantitative Score"].median()
    
    conditions = [
        (df["Qualitative Score"] >= qual_median) & (df["Quantitative Score"] >= quant_median),
        (df["Qualitative Score"] < qual_median) & (df["Quantitative Score"] >= quant_median),
        (df["Qualitative Score"] >= qual_median) & (df["Quantitative Score"] < quant_median),
        (df["Qualitative Score"] < qual_median) & (df["Quantitative Score"] < quant_median)
    ]
    
    choices = [
        "Top Tier (High Qual, High Quant)",
        "Quant Leaders (Low Qual, High Quant)",
        "Qualitative Gems (High Qual, Low Quant)",
        "Development Area (Low Qual, Low Quant)"
    ]
    
    df["Quadrant"] = pd.Series(np.select(conditions, choices, default="N/A"), index=df.index)
    logger.info(f"Quadrant distribution:\n{df['Quadrant'].value_counts().to_string()}")
    
    return df

def main():
    """
    Main function to combine qualitative and quantitative scores.
    """
    # === Configuration ===
    qual_path = Path("outputs/qualitative_scored.csv")
    quant_path = Path("outputs/sma_scored.csv")
    output_path = Path("outputs/combined_scores.csv")
    config = get_combination_config()
    
    # === Execution Pipeline ===
    df_qual, df_quant = load_data(qual_path, quant_path)
    df_merged = merge_scores(df_qual, df_quant)
    df_combined = calculate_combined_score(df_merged, config)
    df_final = assign_quadrant(df_combined)
    
    # Sort for a clean final report
    df_final = df_final.sort_values(by="Combined Score", ascending=False)
    
    # === Save Results ===
    output_path.parent.mkdir(exist_ok=True)
    df_final.to_csv(output_path, index=False)
    logger.info(f"Combined scores saved to {output_path}")
    
    # === Reporting ===
    print("\n--- Sample of Combined Scores ---")
    print(df_final.head().to_string())
    
    logger.info("Score combination process completed successfully.")

if __name__ == "__main__":
    main()
