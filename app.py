import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import base64

# --- Page Configuration ---
st.set_page_config(
    page_title="SMA Scoring Engine",
    page_icon="📊",
    layout="wide"
)

# --- Add scripts directory to path ---
sys.path.append(str(Path(__file__).resolve().parent / "scripts"))
from scripts.scoring_engine import main as quant_main, get_scoring_config, validate_weights, calculate_scores as calculate_quant_scores, calculate_composite_score as calculate_quant_composite_score, apply_tier_logic
from scripts.qualitative_scoring_engine import main as qual_main, get_qualitative_config, calculate_final_score as calculate_qual_final_score
from scripts.combine_scores import main as combine_scores_main, get_combination_config, calculate_combined_score

# --- Helper Functions ---

def load_local_css(file_name):
    """Loads a local CSS file."""
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file not found: {file_name}")

def get_table_download_link(df, filename, text):
    """Generates a link allowing the data in a given panda dataframe to be downloaded."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'

@st.cache_data
def load_data(file_path):
    """Loads the combined scores, caching the result."""
    return pd.read_csv(file_path) if file_path.exists() else None

def get_tier_explanation(score: float, thresholds: dict) -> tuple[str, str]:
    """Assigns a tier and provides a justification based on a fund's score."""
    tier1_cutoff = thresholds["tier1_cutoff"]
    tier2_cutoff = thresholds["tier2_cutoff"]

    if score >= tier1_cutoff:
        tier = "Tier 1"
        justification = "Ranks in the top tier of its peers, demonstrating exceptional overall performance."
    elif score >= tier2_cutoff:
        tier = "Tier 2"
        justification = "Ranks in the upper-middle tier, showing strong results and solid potential."
    else:
        tier = "Tier 3"
        justification = "Ranks in the bottom tier, indicating significant room for improvement."
    return tier, justification

def apply_tier_and_justification(df, tier1_pct, tier2_pct):
    """Calculates tiers and justifications based on dynamic percentile cutoffs."""
    thresholds = {
        "tier1_cutoff": df["Combined Score"].quantile(tier1_pct / 100),
        "tier2_cutoff": df["Combined Score"].quantile(tier2_pct / 100),
    }
    tier_data = df["Combined Score"].apply(lambda score: get_tier_explanation(score, thresholds))
    df["Tier"] = [item[0] for item in tier_data]
    df["Justification"] = [item[1] for item in tier_data]
    return df

def run_scoring_for_new_fund(qual_df, quant_df):
    """Re-scores a single new fund provided as dataframes."""
    # Quantitative Scoring
    quant_config = get_scoring_config()
    total_weight = validate_weights(quant_config)
    df_quant_scored = calculate_quant_scores(quant_df, quant_config)
    df_quant_composite = calculate_quant_composite_score(df_quant_scored, quant_config, total_weight)
    df_tiered = apply_tier_logic(df_quant_composite)
    
    # Qualitative Scoring
    qual_config = get_qualitative_config()
    df_qual_scored = calculate_qual_final_score(qual_df, qual_config)
    
    # Combine Scores
    df_quant_scored.rename(columns={"Name": "Fund Name"}, inplace=True)
    merged_df = pd.merge(df_tiered[["Fund Name", "Quantitative Score"]], df_qual_scored[["Fund Name", "Qualitative Score"]], on="Fund Name", how="inner")
    
    combination_config = get_combination_config()
    combined_df = calculate_combined_score(merged_df, combination_config)
    
    return combined_df

def dataframe_with_podium_styles(df):
    """Applies custom styles to the dataframe for tier-based highlighting."""
    def get_row_style(row):
        style = ''
        if row["Tier"] == "Tier 1":
            style = 'background-color: #E8F5E9;'
        elif row["Tier"] == "Tier 2":
            style = 'background-color: #FFFDE7;'
        elif row["Tier"] == "Tier 3":
            style = 'background-color: #FFEBEE;'
        
        if 'is_new' in row and row['is_new']:
            style += 'border: 2px solid #1E88E5;'
            
        return [style] * len(row)
    
    return df.style.apply(get_row_style, axis=1)

# --- UI Rendering Functions ---

def render_header():
    """Renders the main application header."""
    st.markdown(
        """
        <div class="header">
            <h1>📊 SMA Scoring Engine Dashboard</h1>
            <p>An interactive tool to analyze, filter, and understand fund performance based on our proprietary scoring model.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def main():
    """Main function to run the Streamlit application."""
    load_local_css("style.css")
    render_header()

    # Initialize session state for the new fund
    if 'new_fund_df' not in st.session_state:
        st.session_state.new_fund_df = None

    # Check for data and generate if missing
    combined_scores_path = Path("outputs/combined_scores.csv")
    if not combined_scores_path.exists():
        st.warning("Data not found. Running scoring pipeline...")
        with st.spinner("Executing scoring scripts..."):
            quant_main()
            qual_main()
            combine_scores_main()
        st.success("Data generated successfully!")
        st.cache_data.clear()

    df_combined = load_data(combined_scores_path)

    if df_combined is None:
        st.error("Failed to load or generate scoring data. Please check the scripts.")
        return

    # --- Sidebar Controls ---
    st.sidebar.header("⚙️ Controls & Filters")

    with st.sidebar.expander("Tier Percentile Cutoffs", expanded=True):
        tier1_pct = st.sidebar.slider("Tier 1 Cutoff (%ile)", 50, 100, 75, 1)
        tier2_pct = st.sidebar.slider("Tier 2 Cutoff (%ile)", 0, tier1_pct - 1, 50, 1)

    with st.sidebar.expander("Compare a New Fund"):
        uploaded_qual_file = st.file_uploader("Upload New Qualitative Data (CSV)", type="csv")
        uploaded_quant_file = st.file_uploader("Upload New Quantitative Data (CSV)", type="csv")

        if st.button("Score and Compare"):
            if uploaded_qual_file and uploaded_quant_file:
                try:
                    new_qual_df = pd.read_csv(uploaded_qual_file)
                    new_quant_df = pd.read_csv(uploaded_quant_file)
                    
                    with st.spinner("Scoring new fund..."):
                        newly_scored_df = run_scoring_for_new_fund(new_qual_df, new_quant_df)
                        newly_scored_df['is_new'] = True
                        st.session_state.new_fund_df = newly_scored_df
                        st.success("New fund scored successfully!")

                except Exception as e:
                    st.error(f"Error scoring new fund: {e}")
            else:
                st.warning("Please upload both qualitative and quantitative files.")

    # Append new fund if it exists in session state
    if st.session_state.new_fund_df is not None:
        df_combined = pd.concat([df_combined, st.session_state.new_fund_df], ignore_index=True)

    # Calculate tiers for the potentially expanded dataframe
    df_with_tiers = apply_tier_and_justification(df_combined.copy(), tier1_pct, tier2_pct)

    st.sidebar.header("Filters")
    search_term = st.sidebar.text_input("Search by Fund Name")
    
    unique_tiers = sorted(df_with_tiers["Tier"].unique())
    selected_tiers = st.sidebar.multiselect("Filter by Tier", unique_tiers, default=unique_tiers)

    # --- Main Content Rendering ---
    st.header("Fund Performance Overview")

    filtered_df = df_with_tiers[df_with_tiers["Tier"].isin(selected_tiers)]
    if search_term:
        filtered_df = filtered_df[filtered_df["Fund Name"].str.contains(search_term, case=False, na=False)]

    # Prepare dataframe for display
    display_cols = ['Fund Name', 'Combined Score', 'Tier', 'Justification']
    if 'is_new' in filtered_df.columns:
        display_cols.append('is_new')

    st.dataframe(
        dataframe_with_podium_styles(filtered_df[display_cols]), 
        use_container_width=True,
        hide_index=True,
        column_config={"is_new": None}
    )

    st.markdown(get_table_download_link(filtered_df.drop(columns=['is_new'], errors='ignore'), "sma_scores.csv", "📥 Download as CSV"), unsafe_allow_html=True)

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


if __name__ == "__main__":
    main()
