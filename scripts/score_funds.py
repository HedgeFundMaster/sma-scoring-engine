import pandas as pd

def read_data(file_path):
    df = pd.read_csv(file_path)
    print(df.head())
    return df

if __name__ == "__main__":
    df = read_data("Qualitative Scoring.csv")

qual_mapping = {
    "Very High": 4,
    "High": 3,
    "Medium-High": 2.5,
    "Medium": 2,
    "Moderate": 2,
    "Low": 1,
    "—": 0,
    "N/A": 0
}

def normalize_scores(df):
    columns_to_normalize = [
        "Team Depth", "Transparency & Reporting", "Investment Philosophy Clarity", "Consistency of Process"
    ]
    for col in columns_to_normalize:
        df[col + "_Score"] = df[col].map(qual_mapping)
    return df

def compute_composite_score(df):
    df["Composite Score"] = df[[
        "Team Depth_Score", "Transparency & Reporting_Score",
        "Investment Philosophy Clarity_Score", "Consistency of Process_Score"
    ]].mean(axis=1)
    return df

