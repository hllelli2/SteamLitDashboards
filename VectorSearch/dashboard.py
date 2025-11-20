# This is going to be where the stacked bar chart will be


# What I need to do:
# 1. Import necessary libraries
# 2. Load the data
# a These are in separate parquet files, I will want to subset based on species later on
# I'll need to load them all and concatenate them anyway. maybe get the counts for the barplot and the organism
# This way I can parse the files only once and retain the useful information
# 3. create a stacked barplot of the data


import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.title("Matching Product Descriptions from Various Databases")

PLOT_CACHE = {}


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


# @st.cache_data
def load_data(file_paths):
    """
    Load data from multiple Parquet files and concatenate them into a single DataFrame.
    Args:
        file_paths (list): List of paths to the Parquet files.
    Returns:
        pd.DataFrame: Loaded data as a pandas DataFrame.
    """
    df_list = []
    for file_path in file_paths:
        df = pd.read_parquet(file_path)
        df_list.append(df)
    combined_df = pd.concat(df_list, ignore_index=True)
    return combined_df


@st.cache_data
def condense_data(df):
    # keep the Gene ID organism, Sourc_File, best_match_value, search_term, best_match_id and best_match_score columns
    condensed_df = df[
        [
            "Gene ID",
            "Organism",
            "Source_File",
            "best_match_value",
            "search_term",
            "best_match_id",
            "best_match_score",
        ]
    ]

    condensed_df["Source_File"] = (
        condensed_df["Source_File"]
        .map(SOURCE_FILE_TEXT_MAP)
        .fillna(condensed_df["Source_File"])
    )
    return condensed_df


def make_match_bin_chart(condensed_df, selected_org=None):

    if selected_org == None:
        if PLOT_CACHE.get("All", False):
            return PLOT_CACHE["All"]
    else:
        if PLOT_CACHE.get(selected_org, False):
            return PLOT_CACHE[selected_org]

    # Optional organism filtering
    if selected_org and selected_org != "All":
        df_sub = condensed_df[condensed_df["Organism"] == selected_org].copy()
    else:
        df_sub = condensed_df.copy()

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

    selected_org = "All" if selected_org is not None else selected_org
    PLOT_CACHE[selected_org] = fig

    return fig


def sample_dataframe(condensed_df, selected_org=None, selected_source=None):
    df_sub = condensed_df.copy()

    if selected_org and selected_org != "All":
        df_sub = df_sub[df_sub["Organism"] == selected_org]

    if selected_source and selected_source != "All":
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

    df_sub = df_sub.set_index("Gene ID")
    return df_sub


def app():
    input_data_dir = Path(__file__).parent.parent.joinpath("input_data")
    data_dir = input_data_dir.joinpath("vs_tsvs")
    file_paths = list(data_dir.glob("*.parquet"))
    df = load_data(file_paths)
    st.write(f"Loaded {len(df)} records from {len(file_paths)} files.")
    condensed_df = condense_data(df)

    # organism files for subsetting later

    col1, col2 = st.columns([3, 1])

    with col2:
        selected_org = st.selectbox(
            "Select Organism", ["All"] + sorted(condensed_df["Organism"].unique())
        )

    with col1:
        fig = make_match_bin_chart(condensed_df, selected_org)

        # Render the nice Streamlit Plotly chart
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns([3, 1])

    with col2:
        selected_source = st.selectbox(
            "Select Source", ["All"] + sorted(condensed_df["Source_File"].unique())
        )
    with col1:
        # do a dataframe filter based on the selections
        sampled_df = sample_dataframe(
            condensed_df, selected_org=selected_org, selected_source=selected_source
        )
        st.write(
            f"Displaying {len(sampled_df)} records for Organism: {selected_org} and Source: {selected_source}"
        )
        st.dataframe(sampled_df)
