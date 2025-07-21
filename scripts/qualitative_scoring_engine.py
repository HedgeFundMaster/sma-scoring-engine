import pandas as pd
from pathlib import Path
import logging
import re
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_qualitative_config() -> Dict[str, Any]:
    """
    Defines and returns the configuration for qualitative scoring.
    
    This includes mappings for converting text ratings to numerical scores
    and weights for each qualitative attribute.
    
    Returns:
        dict: A dictionary containing score mappings and attribute weights.
    """
    score_mappings = {
        "Team Depth": {"Large": 4, "Medium-High": 3, "Medium": 2, "Small": 1},
        "Transparency & Reporting": {"Very High": 4, "High": 3, "Medium-High": 2, "Medium": 1, "Low": 0},
        "Consistency of Process": {"Very Strong": 4, "Strong": 3, "Moderate": 2, "Still developing": 1, "Too early to judge": 0, "Developing": 1, "Still forming": 1}
    }
    
    weights = {
        "Manager Tenure Score": 0.20,
        "Team Depth Score": 0.25,
        "Transparency & Reporting Score": 0.20,
        "Consistency of Process Score": 0.35
    }
    
    return {"mappings": score_mappings, "weights": weights}

def parse_tenure(tenure_str: Any) -> float:
    """
    Parses a string to extract a numerical value for manager tenure.
    Handles formats like '10+', '<5', '5-10'.
    
    Args:
        tenure_str (Any): The input string or value.
        
    Returns:
        float: The extracted or averaged numerical tenure.
    """
    if not isinstance(tenure_str, str):
        return 0.0
    
    numbers = [float(n) for n in re.findall(r'\d+\.?\d*', tenure_str)]
    if numbers:
        return sum(numbers) / len(numbers)
    return 0.0

def load_and_clean_data(file_path: Path) -> pd.DataFrame:
    """
    Loads and cleans the qualitative data from the CSV file.
    
    It specifically reads the first 26 rows to avoid the formatting issues
    in the latter half of the file.
    
    Args:
        file_path (Path): The path to the input CSV file.
        
    Returns:
        pd.DataFrame: A cleaned dataframe ready for scoring.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
        
    logger.info(f"Loading qualitative data from: {file_path}")
    # The CSV has an inconsistent format; the first 26 rows are structured correctly.
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    
    # Clean whitespace from all text-based columns
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].str.strip()
        
    logger.info(f"Loaded and cleaned {len(df)} records.")
    return df

def score_attribute(series: pd.Series, mapping: Dict[str, int]) -> pd.Series:
    """
    Scores a qualitative attribute based on a provided mapping.
    
    Args:
        series (pd.Series): The series containing text-based ratings.
        mapping (dict): The dictionary to map text to numerical scores.
        
    Returns:
        pd.Series: A series of numerical scores.
    """
    return series.map(mapping).fillna(0).astype(int)

def calculate_final_score(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Calculates the final qualitative score based on attribute scores and weights.
    
    Args:
        df (pd.DataFrame): The cleaned dataframe.
        config (dict): The configuration dictionary with mappings and weights.
        
    Returns:
        pd.DataFrame: A dataframe with the final qualitative scores.
    """
    mappings = config["mappings"]
    weights = config["weights"]
    
    scored_df = df[["Fund Name"]].copy()
    
    # Score Manager Tenure (numerical, not mapped)
    tenure_scores = df["Manager Tenure (Years)"].apply(parse_tenure)
    # Normalize tenure score (0-1 scale, capped at 20 years for max score)
    scored_df["Manager Tenure Score"] = (tenure_scores / 20).clip(0, 1)

    # Score other attributes using mappings
    for attribute, mapping in mappings.items():
        scored_df[f"{attribute} Score"] = score_attribute(df[attribute], mapping)

    # Normalize mapped scores to a 0-1 scale
    for col in scored_df.columns:
        if col != "Fund Name" and "Tenure" not in col:
            max_possible_score = max(mappings[col.replace(" Score", "")].values())
            if max_possible_score > 0:
                scored_df[col] = scored_df[col] / max_possible_score

    # Calculate weighted composite score
    total_weight = sum(weights.values())
    scored_df["Qualitative Score"] = 0
    for col, weight in weights.items():
        if col in scored_df.columns:
            scored_df["Qualitative Score"] += scored_df[col] * weight
            
    # Normalize by total weight and scale to 100
    if total_weight > 0:
        scored_df["Qualitative Score"] = (scored_df["Qualitative Score"] / total_weight) * 100

    logger.info("Calculated final qualitative scores.")
    return scored_df

def main():
    """
    Main function to execute the qualitative scoring pipeline.
    """
    # === Configuration ===
    input_path = Path("data/Qualitative Scoring.csv")
    output_path = Path("outputs/qualitative_scored.csv")
    config = get_qualitative_config()
    
    # === Execution Pipeline ===
    df = load_and_clean_data(input_path)
    df_scored = calculate_final_score(df, config)
    
    # === Save Results ===
    output_path.parent.mkdir(exist_ok=True)
    df_scored.to_csv(output_path, index=False)
    logger.info(f"Qualitative scores saved to {output_path}")
    
    # === Reporting ===
    print("\n--- Sample Qualitative Scores ---")
    print(df_scored.head())
    
    logger.info("Qualitative scoring completed successfully.")

if __name__ == "__main__":
    main()
