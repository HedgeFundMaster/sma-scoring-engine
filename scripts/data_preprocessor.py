import pandas as pd
from pathlib import Path
import re
import sys

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

# Input files
QUANT_RAW_PATH = DATA_DIR / "sma_data_structured.csv"
QUAL_RAW_PATH = DATA_DIR / "Qualitative Scoring.csv"

# Output files
CLEANED_QUANT_PATH = OUTPUT_DIR / "quantitative_data_cleaned.csv"
CLEANED_QUAL_PATH = OUTPUT_DIR / "qualitative_data_cleaned.csv"

def clean_column_names(df):
    """Standardizes column names to be more Python-friendly."""
    cols = df.columns
    new_cols = [' '.join(col.strip().split()).title() for col in cols]
    df.columns = new_cols
    return df

def parse_manager_tenure(series):
    """
    Parses manager tenure strings (e.g., '5-10', '25+', '~5') into a numerical
    value, taking the lower bound.
    """
    def extract_tenure(x):
        if isinstance(x, str):
            numbers = re.findall(r'\d+', x)
            if numbers:
                return int(numbers[0])
        return 0
    return series.apply(extract_tenure)

def clean_quantitative_data(input_path, output_path):
    """
    Cleans the quantitative data file:
    - Skips the initial blank lines.
    - Standardizes column names.
    - Renames 'Name' to 'Fund Name'.
    - Saves the cleaned data.
    """
    try:
        if not input_path.exists():
            print(f"❌ Error: Raw quantitative data file not found at {input_path}", file=sys.stderr)
            return None

        df = pd.read_csv(input_path, skip_blank_lines=True)
        
        df = clean_column_names(df)
        
        if 'Name' in df.columns:
            df.rename(columns={'Name': 'Fund Name'}, inplace=True)
            
        if 'Fund Name' in df.columns:
            cols = ['Fund Name'] + [col for col in df.columns if col != 'Fund Name']
            df = df[cols]

        output_path.parent.mkdir(exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"✅ Quantitative data cleaned and saved to {output_path}")
        return df

    except Exception as e:
        print(f"❌ An unexpected error occurred while cleaning quantitative data: {e}", file=sys.stderr)
        return None

def clean_qualitative_data(input_path, output_path):
    """
    Cleans the qualitative data file:
    - Standardizes column names.
    - Parses 'Manager Tenure (Years)'.
    - Saves the cleaned data.
    """
    try:
        if not input_path.exists():
            print(f"❌ Error: Raw qualitative data file not found at {input_path}", file=sys.stderr)
            return None

        df = pd.read_csv(input_path)
        
        df = clean_column_names(df)
        
        if 'Manager Tenure (Years)' in df.columns:
            df['Manager Tenure (Years)'] = parse_manager_tenure(df['Manager Tenure (Years)'])
        
        output_path.parent.mkdir(exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"✅ Qualitative data cleaned and saved to {output_path}")
        return df

    except Exception as e:
        print(f"❌ An unexpected error occurred while cleaning qualitative data: {e}", file=sys.stderr)
        return None

def main():
    """Main function to run the data preprocessing steps."""
    print("--- Starting Data Preprocessing ---")
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    clean_quantitative_data(QUANT_RAW_PATH, CLEANED_QUANT_PATH)
    clean_qualitative_data(QUAL_RAW_PATH, CLEANED_QUAL_PATH)
    
    print("--- Data Preprocessing Complete ---")

if __name__ == "__main__":
    main()
