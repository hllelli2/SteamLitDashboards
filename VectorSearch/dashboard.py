import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.title("Matching VPDB Product Descriptions From Databases")

SOURCE_FILE_TEXT_MAP = {
    "entry.tsv": "InterPro",
    "uniprot_trembl.fasta": "UniProtKB-Trembl",
    "PFAM.tsv": "PFAM",
    "PANTHER.tsv": "PANTHER",
    "DMFly.tsv": "FlyBase",
    "NCBIFAM.tsv": "NCBI Gene Family",
    "uniprot_sprot.fasta": "UniProtKB-SwissProt",
    "CGD.tsv": "CGD",
    "PIRSF.tsv": "PIRSF",
    "SUPERFAMILY.tsv": "SUPERFAMILY",
    "CATH-Gene3D.tsv": "CATH-Gene3D",
    "CDD.tsv": "CDD",
    "SMART.tsv": "SMART",
    "PRINTS.tsv": "PRINTS",
    "HAMAP.tsv": "HAMAP",
    "SFS.tsv": "SFLD",
    "SGD_features.tab": "SGD",
    "PROSITE_profiles.tsv": "PROSITE Profiles",
    "PROSITE_patterns.tsv": "PROSITE Patterns",
    "AntiFam.tsv": "AntiFam",
    "SFLD.tsv": "SFLD",
}


# ------------------------------
# SAFE CACHING FUNCTIONS
# ------------------------------


@st.cache_data(show_spinner="Loading data…")
def load_data(file_paths):
    """Load and concatenate multiple parquet files safely."""
    df_list = []
    for fp in file_paths:
        df_list.append(pd.read_parquet(fp))
    return pd.concat(df_list, ignore_index=True)


@st.cache_data(show_spinner="Condensing data…")
def condense_data(df):
    """Keep required columns and map clean source names."""
    cols = [
        "Gene ID",
        "Organism",
        "Source_File",
        "best_match_value",
        "search_term",
        "best_match_id",
        "best_match_score",
    ]
    condensed = df[cols].copy()

    condensed["Source_File"] = (
        condensed["Source_File"]
        .map(SOURCE_FILE_TEXT_MAP)
        .fillna(condensed["Source_File"])
    )
    return condensed


@st.cache_data(show_spinner="Computing chart…")
def make_match_bin_chart(condensed_df, selected_org):
    """Generate stacked bar chart & cache the figure safely."""

    if selected_org != "All":
        df_sub = condensed_df[condensed_df["Organism"] == selected_org]
    else:
        df_sub = condensed_df

    df_sub = df_sub.copy()
    df_sub["best_match_score"] = pd.to_numeric(
        df_sub["best_match_score"], errors="coerce"
    )

    def assign_bin(x):
        if x == 1.0:
            return "1.0"
        elif 0.8 <= x < 1.0:
            return "0.8–1.0"
        elif 0.5 <= x < 0.8:
            return "0.5–0.8"
        else:
            return "<0.5"

    df_sub["match_bin"] = df_sub["best_match_score"].apply(assign_bin)

    allowed_bins = ["1.0", "0.8–1.0", "0.5–0.8"]
    df_sub = df_sub[df_sub["match_bin"].isin(allowed_bins)]

    counts = (
        df_sub.groupby(["Source_File", "match_bin"]).size().reset_index(name="count")
    )

    bin_order = ["1.0", "0.8–1.0", "0.5–0.8"]
    counts["match_bin"] = pd.Categorical(
        counts["match_bin"], categories=bin_order, ordered=True
    )
    counts = counts.sort_values(by=["match_bin", "count"], ascending=[True, False])

    fig = px.bar(
        counts,
        x="Source_File",
        y="count",
        color="match_bin",
        category_orders={"match_bin": bin_order},
        labels={"count": "Gene ID Count", "Source_File": "Source"},
    )

    fig.update_layout(
        barmode="stack",
        width=1000,
        height=600,
        xaxis_tickangle=45,
    )

    return fig


def sample_dataframe(condensed_df, selected_org, selected_source):
    """Return a small sample for display."""
    df_sub = condensed_df

    if selected_org != "All":
        df_sub = df_sub[df_sub["Organism"] == selected_org]

    if selected_source != "All":
        df_sub = df_sub[df_sub["Source_File"] == selected_source]

    df_sub = df_sub.sample(n=10) if len(df_sub) > 10 else df_sub

    df_sub = df_sub.rename(
        columns={
            "best_match_value": "Best Match Description",
            "search_term": "VPDB Product Description Searched",
            "best_match_id": "Best Match ID",
            "best_match_score": "Dice similarity score",
            "Source_File": "Source Database",
        }
    )

    return df_sub.set_index("Gene ID")


# ------------------------------
# MAIN APP
# ------------------------------


def app():
    # Cloud-safe: show something immediately so health checks pass
    st.write("Preparing application…")

    input_data_dir = Path(__file__).parent.parent / "input_data"
    file_paths = list((input_data_dir / "vs_tsvs").glob("*.parquet"))

    df = load_data(file_paths)
    st.write(f"Loaded {len(df):,} records from {len(file_paths)} files.")

    condensed_df = condense_data(df)

    # -------------------
    # Organism selector
    # -------------------
    col1, col2 = st.columns([3, 1])

    with col2:
        organisms = sorted(condensed_df["Organism"].unique())
        selected_org = st.selectbox("Select Organism", ["All"] + organisms)

    with col1:
        fig = make_match_bin_chart(condensed_df, selected_org)
        st.plotly_chart(fig, use_container_width=True)

    # -------------------
    # Sample table section
    # -------------------
    col1, col2 = st.columns([3, 1])

    with col2:
        sources = sorted(condensed_df["Source_File"].unique())
        selected_source = st.selectbox("Select Source", ["All"] + sources)

    with col1:
        sampled_df = sample_dataframe(condensed_df, selected_org, selected_source)
        st.write(
            f"Displaying {len(sampled_df)} records for Organism: {selected_org} "
            f"and Source: {selected_source}"
        )
        st.dataframe(sampled_df)


# Run the app
app()
