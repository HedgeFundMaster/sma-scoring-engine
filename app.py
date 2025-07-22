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

# --- Path Definitions ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

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
    if df is None:
        return ""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}" style="color: #A9CCE3; text-decoration: none;">{text}</a>'

@st.cache_data
def load_and_process_data():
    """
    Loads final scores and prepares data for the dashboard.
    This function assumes all necessary files exist.
    """
    # Define paths
    combined_scores_path = OUTPUT_DIR / "combined_scores.csv"
    qual_cleaned_path = OUTPUT_DIR / "qualitative_data_cleaned.csv"
    quant_cleaned_path = OUTPUT_DIR / "quantitative_data_cleaned.csv"

    try:
        df = pd.read_csv(combined_scores_path)
        qual_df = pd.read_csv(qual_cleaned_path)
        quant_df = pd.read_csv(quant_cleaned_path)

        # --- Robustly Merge Supplementary Data ---
        # Merge Manager Tenure if available
        if 'Manager Tenure (Years)' in qual_df.columns and 'Fund Name' in qual_df.columns:
            df = pd.merge(df, qual_df[['Fund Name', 'Manager Tenure (Years)']], on="Fund Name", how="left")
        else:
            st.warning("Column 'Manager Tenure (Years)' not found. Tenure filter will be disabled.")

        # Merge Sharpe Ratio if available
        if 'Historical Sharpe Ratio (3Y)' in quant_df.columns and 'Fund Name' in quant_df.columns:
            df = pd.merge(df, quant_df[['Fund Name', 'Historical Sharpe Ratio (3Y)']], on='Fund Name', how="left")
        else:
            st.warning("Column 'Historical Sharpe Ratio (3Y)' not found. Sharpe Ratio filter will be disabled.")

        # Assign Tiers
        tier1_cutoff = df["Combined Score"].quantile(0.75)
        tier2_cutoff = df["Combined Score"].quantile(0.50)
        
        def assign_tier(score):
            if score >= tier1_cutoff: return "Tier 1"
            elif score >= tier2_cutoff: return "Tier 2"
            else: return "Tier 3"
            
        df['Tier'] = df['Combined Score'].apply(assign_tier)
        
        print("✅ Data loaded and processed successfully.")
        return df

    except FileNotFoundError as e:
        st.error(f"A required data file was not found: {e.filename}. Please run the main scoring pipeline first.")
        return None
    except Exception as e:
        st.error(f"An error occurred while loading data: {e}")
        return None

# --- UI Rendering ---
def render_header():
    st.markdown('<div class="header"><h1>FUND RANKING DASHBOARD</h1></div>', unsafe_allow_html=True)

def render_footer():
    st.markdown("""
        <div class="footer">
            <p>&copy; 2025 Your Company Name. All Rights Reserved.</p>
            <p>Disclaimer: This tool is for informational purposes only.</p>
        </div>
    """, unsafe_allow_html=True)

def main():
    load_local_css("style.css")
    render_header()

    df = load_and_process_data()

    if df is None:
        st.error("Failed to load data. Please run the main scoring pipeline by executing `python main.py` in your terminal.")
        st.stop()
    
    # --- Sidebar ---
    st.sidebar.title("Controls & Filters")
    unique_tiers = sorted(df["Tier"].unique())
    selected_tiers = st.sidebar.multiselect("Filter by Tier", unique_tiers, default=unique_tiers)

    # --- Conditional Filters ---
    sharpe_col = 'Historical Sharpe Ratio (3Y)'
    tenure_col = 'Manager Tenure (Years)'
    selected_sharpe = None
    tenure_filter = False

    if sharpe_col in df.columns and df[sharpe_col].notna().any():
        min_sharpe, max_sharpe = df[sharpe_col].min(), df[sharpe_col].max()
        selected_sharpe = st.sidebar.slider(
            "Filter by 3Y Sharpe Ratio", 
            float(min_sharpe), float(max_sharpe), (float(min_sharpe), float(max_sharpe))
        )

    if tenure_col in df.columns and df[tenure_col].notna().any():
        tenure_filter = st.sidebar.checkbox("Filter by Manager Tenure > 10 years")

    # --- Main Logic ---
    filtered_df = df[df["Tier"].isin(selected_tiers)]
    
    if selected_sharpe:
        min_s, max_s = selected_sharpe
        filtered_df = filtered_df[
            (filtered_df[sharpe_col].fillna(min_s) >= min_s) &
            (filtered_df[sharpe_col].fillna(max_s) <= max_s)
        ]

    if tenure_filter:
        filtered_df = filtered_df[filtered_df[tenure_col].fillna(0) > 10]

    st.header("Fund Performance Overview")

    col1, col2 = st.columns([3, 1])
    search_term = col1.text_input("Search by Fund Name", placeholder="Type to filter funds...")
    sort_by = col2.selectbox("Sort by", ["Combined Score", "Qualitative Score", "Quantitative Score"], index=0)

    if search_term:
        filtered_df = filtered_df[filtered_df["Fund Name"].str.contains(search_term, case=False, na=False)]

    filtered_df = filtered_df.sort_values(by=sort_by, ascending=False)

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fund Name": st.column_config.TextColumn(width="large"),
            "Combined Score": st.column_config.NumberColumn(format="%.2f"),
            "Qualitative Score": st.column_config.NumberColumn(format="%.2f"),
            "Quantitative Score": st.column_config.NumberColumn(format="%.2f"),
            "Manager Tenure (Years)": None,
            "Historical Sharpe Ratio (3Y)": None
        }
    )

    st.markdown(get_table_download_link(filtered_df, "filtered_fund_scores.csv", "📥 Export Current View to CSV"), unsafe_allow_html=True)
    render_footer()

if __name__ == "__main__":
    main()
