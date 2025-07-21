import pandas as pd
from pathlib import Path

def get_tier_thresholds(scores: pd.Series) -> dict:
    """
    Calculates the percentile thresholds for tiering based on a series of scores.

    Args:
        scores (pd.Series): A pandas Series containing the combined scores.

    Returns:
        dict: A dictionary with the 75th and 50th percentile values.
    """
    return {
        "tier1_cutoff": scores.quantile(0.75),  # Top 25%
        "tier2_cutoff": scores.quantile(0.50),  # Top 50%
    }

def get_tier_explanation(score: float, thresholds: dict) -> tuple[str, str]:
    """
    Assigns a tier and provides a justification based on a fund's score.

    Args:
        score (float): The combined score of the fund.
        thresholds (dict): A dictionary containing the percentile cutoffs.

    Returns:
        tuple[str, str]: A tuple containing the tier name and the justification string.
    """
    tier1_cutoff = thresholds["tier1_cutoff"]
    tier2_cutoff = thresholds["tier2_cutoff"]

    if score >= tier1_cutoff:
        tier = "Tier 1"
        justification = (
            "This fund ranks in the top 25% of its peers, demonstrating exceptional "
            "overall performance in both quantitative and qualitative metrics."
        )
    elif score >= tier2_cutoff:
        tier = "Tier 2"
        justification = (
            "This fund ranks in the top 50% of its peers, showing strong overall results "
            "that place it in the upper half of the funds analyzed."
        )
    else:
        tier = "Tier 3"
        justification = (
            "This fund is in the bottom 50% of its peers, indicating there are significant "
            "opportunities for improvement across its scoring metrics."
        )
    return tier, justification

def main():
    """
    Main function to generate a full tier explanation report for all funds.
    """
    print("--- Tier Explanation Engine ---")
    
    # Define paths
    combined_scores_path = Path("outputs/combined_scores.csv")
    report_path = Path("outputs/tier_explanation_report.csv")
    
    # Load the scored data
    if not combined_scores_path.exists():
        print(f"Error: The file '{combined_scores_path}' was not found.")
        print("Please run the main scoring scripts first.")
        return

    df = pd.read_csv(combined_scores_path)
    
    # Ensure the 'Combined Score' column exists
    if "Combined Score" not in df.columns:
        print("Error: 'Combined Score' column not found in the data.")
        return

    # Calculate thresholds from the full dataset
    thresholds = get_tier_thresholds(df["Combined Score"])
    
    print(f"\nCalculated Thresholds:")
    print(f"  - Tier 1 Cutoff (Top 25%): {thresholds['tier1_cutoff']:.2f}")
    print(f"  - Tier 2 Cutoff (Top 50%): {thresholds['tier2_cutoff']:.2f}\n")

    # Apply the explanation function to all funds
    tier_data = df["Combined Score"].apply(lambda score: get_tier_explanation(score, thresholds))
    
    # Create new columns for the report
    df["Assigned Tier"] = [item[0] for item in tier_data]
    df["Justification"] = [item[1] for item in tier_data]
    
    # Save the full report
    df.to_csv(report_path, index=False)
    
    print(f"Successfully generated full report for {len(df)} funds.")
    print(f"Output saved to: {report_path}")

    # Display the head of the new report
    print("\n--- Sample of Full Report ---")
    print(df[["Fund Name", "Combined Score", "Assigned Tier", "Justification"]].head())


if __name__ == "__main__":
    main()
