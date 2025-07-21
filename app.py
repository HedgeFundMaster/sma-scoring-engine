import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add scripts directory to path to import scoring engines
sys.path.append(str(Path(__file__).resolve().parent / "scripts"))

from scripts.scoring_engine import (
    get_scoring_config,
    validate_weights,
    calculate_scores as calculate_quant_scores,
    calculate_composite_score as calculate_quant_composite_score,
    apply_tier_logic
)
from scripts.qualitative_scoring_engine import (
    get_qualitative_config,
    calculate_final_score as calculate_qual_final_score
)
from scripts.combine_scores import (
    get_combination_config,
    calculate_combined_score,
    assign_quadrant,
    main as combine_scores_main,
)
from scripts.qualitative_scoring_engine import main as qual_main
from scripts.scoring_engine import main as quant_main


def setup_initial_data():
    """
    Checks if the combined scores file exists, and if not, runs the full scoring pipeline.
    """
    combined_scores_path = Path("outputs/combined_scores.csv")
    if not combined_scores_path.exists():
        st.warning("Combined scores file not found. Running the full scoring pipeline now. This may take a moment...")
        with st.spinner("Executing quantitative scoring..."):
            quant_main()
        with st.spinner("Executing qualitative scoring..."):
            qual_main()
        with st.spinner("Combining scores..."):
            combine_scores_main()
        st.success("Scoring pipeline completed successfully!")
        # Clear the cache after regenerating data
        st.cache_data.clear()
    return combined_scores_path

st.set_page_config(layout="wide")

st.title("SMA Scoring Engine Dashboard")

# --- Initial Setup ---
combined_scores_path = setup_initial_data()

@st.cache_data
def load_data(file_path):
    """Loads the combined scores, caching the result."""
    path = Path(file_path)
    if path.exists():
        return pd.read_csv(path)
    return None

def run_scoring_for_new_fund(qual_df, quant_df):
    """
    Re-scores a single new fund provided as dataframes.
    """
    # --- Quantitative Scoring ---
    quant_config = get_scoring_config()
    total_weight = validate_weights(quant_config)
    df_quant_scored = calculate_quant_scores(quant_df, quant_config)
    df_quant_composite = calculate_quant_composite_score(df_quant_scored, quant_config, total_weight)
    df_tiered = apply_tier_logic(df_quant_composite)
    
    # --- Qualitative Scoring ---
    qual_config = get_qualitative_config()
    df_qual_scored = calculate_qual_final_score(qual_df, qual_config)
    
    # --- Combine Scores ---
    df_quant_scored.rename(columns={"Name": "Fund Name"}, inplace=True)
    merged_df = pd.merge(df_tiered[["Fund Name", "Quantitative Score", "Tier"]], df_qual_scored[["Fund Name", "Qualitative Score"]], on="Fund Name", how="inner")
    
    combination_config = get_combination_config()
    combined_df = calculate_combined_score(merged_df, combination_config)
    final_df = assign_quadrant(combined_df)
    
    return final_df

# --- Main Application ---
df_combined = load_data(combined_scores_path)

if df_combined is not None:
    st.sidebar.header("Filters")

    # Tier/Quadrant Filter
    tiers = sorted(df_combined["Quadrant"].unique())
    selected_tiers = st.sidebar.multiselect("Filter by Quadrant", tiers, default=tiers)

    # Score Range Filter
    min_score, max_score = float(df_combined["Combined Score"].min()), float(df_combined["Combined Score"].max())
    score_range = st.sidebar.slider("Filter by Combined Score", min_score, max_score, (min_score, max_score))

    # Fund Name Search
    search_term = st.sidebar.text_input("Search by Fund Name")

    # Apply filters
    filtered_df = df_combined[
        (df_combined["Quadrant"].isin(selected_tiers)) &
        (df_combined["Combined Score"].between(score_range[0], score_range[1]))
    ]

    if search_term:
        filtered_df = filtered_df[filtered_df["Fund Name"].str.contains(search_term, case=False, na=False)]

    st.header("Fund Performance Overview")
    st.dataframe(filtered_df)

    # --- Visualizations ---
    st.header("Top 5 Funds Analysis")
    top_5_df = filtered_df.nlargest(5, "Combined Score")

    if not top_5_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 5 by Combined Score")
            st.bar_chart(top_5_df.set_index("Fund Name")["Combined Score"])
        with col2:
            st.subheader("Scores Breakdown")
            st.bar_chart(top_5_df.set_index("Fund Name")[["Quantitative Score", "Qualitative Score"]])
    else:
        st.warning("No data available for the selected filters to display charts.")

else:
    st.error("Could not find 'outputs/combined_scores.csv'. Please run the scoring scripts first.")

# --- Single Fund Re-scoring ---
st.sidebar.header("Score a New Fund")
uploaded_qual_file = st.sidebar.file_uploader("Upload Qualitative Data (CSV)", type="csv", key="qual")
uploaded_quant_file = st.sidebar.file_uploader("Upload Quantitative Data (CSV)", type="csv", key="quant")

if uploaded_qual_file and uploaded_quant_file:
    try:
        new_qual_df = pd.read_csv(uploaded_qual_file)
        new_quant_df = pd.read_csv(uploaded_quant_file)

        if "Fund Name" not in new_qual_df.columns or "Name" not in new_quant_df.columns:
            st.sidebar.error("CSV files must contain 'Fund Name' (for qualitative) and 'Name' (for quantitative) columns.")
        else:
            with st.spinner("Re-scoring new fund..."):
                new_score_df = run_scoring_for_new_fund(new_qual_df, new_quant_df)
                st.sidebar.subheader("Newly Scored Fund")
                st.sidebar.dataframe(new_score_df)
    except Exception as e:
        st.sidebar.error(f"An error occurred during scoring: {e}")

st.sidebar.info("To start the app, run: `streamlit run app.py` in your terminal.")
