import streamlit as st
import pandas as pd
from pathlib import Path
import base64
import sys

# --- Page Configuration ---
st.set_page_config(
    page_title="Fund Ranking Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Add scripts directory to path ---
sys.path.append(str(Path(__file__).resolve().parent / "scripts"))
from scripts.scoring_engine import get_scoring_config, validate_weights, calculate_scores as calculate_quant_scores, calculate_composite_score as calculate_quant_composite_score, apply_tier_logic
from scripts.qualitative_scoring_engine import get_qualitative_config, calculate_final_score as calculate_qual_final_score
from scripts.combine_scores import get_combination_config, calculate_combined_score

# --- Helper Functions ---

def load_local_css(file_name):
    """Loads a local CSS file."""
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file not found: {file_name}")

def get_table_download_link(df, filename, text):
    """Generates a link to download a DataFrame as a CSV."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}" style="color: #A9CCE3; text-decoration: none;">{text}</a>'

@st.cache_data
def load_all_data():
    """Loads and merges all required data from outputs and data directories."""
    outputs_path = Path("outputs")
    data_path = Path("data")

    combined_scores = pd.read_csv(outputs_path / "combined_scores.csv")
    qual_scores = pd.read_csv(outputs_path / "qualitative_scores.csv")
    quant_scores = pd.read_csv(outputs_path / "quantitative_scores.csv")
    qual_raw = pd.read_csv(data_path / "Qualitative Scoring.csv")
    quant_raw = pd.read_csv(data_path / "sma_data_structured.csv")

    df = pd.merge(combined_scores, qual_scores[['Fund Name', 'Qualitative Score']], on="Fund Name", how="left")
    df = pd.merge(df, quant_scores[['Fund Name', 'Quantitative Score']], on="Fund Name", how="left")
    df = pd.merge(df, qual_raw[['Fund Name', 'Manager Tenure (Years)']], on="Fund Name", how="left")
    df = pd.merge(df, quant_raw[['Name', 'Historical Sharpe Ratio (3Y)']], left_on='Fund Name', right_on='Name', how="left")
    df.drop(columns=['Name'], inplace=True)

    tier1_cutoff = df["Combined Score"].quantile(0.75)
    tier2_cutoff = df["Combined Score"].quantile(0.50)
    
    def assign_tier(score):
        if score >= tier1_cutoff: return "Tier 1"
        elif score >= tier2_cutoff: return "Tier 2"
        else: return "Tier 3"
            
    df['Tier'] = df['Combined Score'].apply(assign_tier)
    df['Manager Tenure (Years)'] = df['Manager Tenure (Years)'].str.extract('(\d+)').astype(float).fillna(0)
    return df

def run_scoring_for_new_fund(qual_df, quant_df):
    """Re-scores a single new fund provided as dataframes."""
    quant_config = get_scoring_config()
    total_weight = validate_weights(quant_config)
    df_quant_scored = calculate_quant_scores(quant_df, quant_config)
    df_quant_composite = calculate_quant_composite_score(df_quant_scored, quant_config, total_weight)
    
    qual_config = get_qualitative_config()
    df_qual_scored = calculate_qual_final_score(qual_df, qual_config)
    
    merged_df = pd.merge(df_quant_composite[["Fund Name", "Quantitative Score"]], df_qual_scored[["Fund Name", "Qualitative Score"]], on="Fund Name", how="inner")
    
    combination_config = get_combination_config()
    combined_df = calculate_combined_score(merged_df, combination_config)
    return combined_df

# --- UI Rendering ---

def render_header():
    st.markdown('<div class="header"><h1>FUND RANKING DASHBOARD</h1></div>', unsafe_allow_html=True)

def render_footer():
    st.markdown("""
        <div class="footer">
            <p>&copy; 2025 Your Company Name. All Rights Reserved.</p>
            <p>Disclaimer: This tool is for informational purposes only and does not constitute investment advice.</p>
        </div>
    """, unsafe_allow_html=True)

def main():
    load_local_css("style.css")
    render_header()

    if 'new_fund_df' not in st.session_state:
        st.session_state.new_fund_df = None

    df = load_all_data()
    
    # --- Sidebar ---
    st.sidebar.header("Controls & Filters")

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

    unique_tiers = sorted(df["Tier"].unique())
    selected_tiers = st.sidebar.multiselect("Filter by Tier", unique_tiers, default=unique_tiers)

    min_sharpe, max_sharpe = float(df['Historical Sharpe Ratio (3Y)'].min()), float(df['Historical Sharpe Ratio (3Y)'].max())
    selected_sharpe = st.sidebar.slider("Filter by 3Y Sharpe Ratio", min_sharpe, max_sharpe, (min_sharpe, max_sharpe))

    tenure_filter = st.sidebar.checkbox("Filter by Manager Tenure > 10 years")

    # --- Main Logic ---
    if st.session_state.new_fund_df is not None:
        df = pd.concat([df, st.session_state.new_fund_df], ignore_index=True)

    filtered_df = df[df["Tier"].isin(selected_tiers)]
    filtered_df = filtered_df[
        (filtered_df['Historical Sharpe Ratio (3Y)'].fillna(min_sharpe) >= selected_sharpe[0]) &
        (filtered_df['Historical Sharpe Ratio (3Y)'].fillna(max_sharpe) <= selected_sharpe[1])
    ]
    if tenure_filter:
        filtered_df = filtered_df[filtered_df['Manager Tenure (Years)'] > 10]

    st.header("Fund Performance Overview")

    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("Search by Fund Name", placeholder="Type to filter funds...")
    with col2:
        sort_by = st.selectbox("Sort by", ["Combined Score", "Qualitative Score", "Quantitative Score"], index=0)

    if search_term:
        filtered_df = filtered_df[filtered_df["Fund Name"].str.contains(search_term, case=False, na=False)]

    filtered_df = filtered_df.sort_values(by=sort_by, ascending=False)

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Combined Score": st.column_config.NumberColumn(format="%.2f", help="The final weighted score."),
            "Qualitative Score": st.column_config.NumberColumn(format="%.2f", help="Score based on factors like team and process."),
            "Quantitative Score": st.column_config.NumberColumn(format="%.2f", help="Score based on performance metrics."),
            "is_new": None,
            "Manager Tenure (Years)": None,
            "Historical Sharpe Ratio (3Y)": None
        }
    )

    st.markdown(get_table_download_link(filtered_df, "filtered_fund_scores.csv", "📥 Export Current View to CSV"), unsafe_allow_html=True)

    render_footer()

if __name__ == "__main__":
    main()
