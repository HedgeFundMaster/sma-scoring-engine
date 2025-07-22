import sys
from pathlib import Path

# Add the scripts directory to the Python path
scripts_dir = Path(__file__).resolve().parent / "scripts"
sys.path.append(str(scripts_dir))

from data_preprocessor import main as preprocess_data
from scoring_engine import main as score_quantitative
from qualitative_scoring_engine import main as score_qualitative
from combine_scores import main as combine_all_scores

def main():
    """
    Main function to run the entire scoring pipeline.
    """
    print("--- Starting SMA Scoring Engine Pipeline ---")
    
    # Step 1: Preprocess the raw data
    print("\n--- Step 1: Preprocessing Data ---")
    preprocess_data()
    
    # Step 2: Run the quantitative scoring engine
    print("\n--- Step 2: Running Quantitative Scoring Engine ---")
    score_quantitative()
    
    # Step 3: Run the qualitative scoring engine
    print("\n--- Step 3: Running Qualitative Scoring Engine ---")
    score_qualitative()
    
    # Step 4: Combine the scores
    print("\n--- Step 4: Combining Scores ---")
    combine_all_scores()
    
    print("\n--- SMA Scoring Engine Pipeline Complete ---")
    print("You can now run the Streamlit app:")
    print("streamlit run app.py")

if __name__ == "__main__":
    main()
