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
from scripts.scoring_engine import main as quant_main
from scripts.qualitative_scoring_engine import main as qual_main
from scripts.combine_scores import main as combine_scores_main

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

def dataframe_with_podium_styles(df):
    """Applies custom styles to the dataframe for tier-based highlighting."""
    def get_row_style(row):
        if row["Tier"] == "Tier 1":
            return ['background-color: #E8F5E9'] * len(row)  # Muted Green
        elif row["Tier"] == "Tier 2":
            return ['background-color: #FFFDE7'] * len(row)  # Muted Yellow
        elif row["Tier"] == "Tier 3":
            return ['background-color: #FFEBEE'] * len(row)  # Muted Red
        return [''] * len(row)
    
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

    # 1. Get dynamic controls first
    with st.sidebar.expander("Tier Percentile Cutoffs", expanded=True):
        tier1_pct = st.sidebar.slider("Tier 1 Cutoff (%ile)", 50, 100, 75, 1)
        tier2_pct = st.sidebar.slider("Tier 2 Cutoff (%ile)", 0, tier1_pct - 1, 50, 1)

    # 2. Calculate tiers based on the dynamic controls
    df_with_tiers = apply_tier_and_justification(df_combined.copy(), tier1_pct, tier2_pct)

    # 3. Create filters based on the *newly calculated* data
    st.sidebar.header("Filters")
    search_term = st.sidebar.text_input("Search by Fund Name")
    
    unique_tiers = sorted(df_with_tiers["Tier"].unique())
    selected_tiers = st.sidebar.multiselect("Filter by Tier", unique_tiers, default=unique_tiers)

    # --- Main Content Rendering ---
    st.header("Fund Performance Overview")

    # Apply filters
    filtered_df = df_with_tiers[df_with_tiers["Tier"].isin(selected_tiers)]
    if search_term:
        filtered_df = filtered_df[filtered_df["Fund Name"].str.contains(search_term, case=False, na=False)]

    # Display styled dataframe
    st.dataframe(dataframe_with_podium_styles(filtered_df[['Fund Name', 'Combined Score', 'Tier', 'Justification']]), use_container_width=True)

    # Download links
    st.markdown(get_table_download_link(filtered_df, "sma_scores.csv", "📥 Download as CSV"), unsafe_allow_html=True)

    # Visualizations
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