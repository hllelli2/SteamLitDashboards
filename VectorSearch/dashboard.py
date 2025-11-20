import streamlit as st
import pandas as pd
import plotly.express as px
import pyarrow.dataset as ds
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

# -------------------------------------
#  SAFE, SCALABLE PARQUET LOADING
# -------------------------------------

REQUIRED_COLS = [
    "Gene ID",
    "Organism",
    "Source_File",
    "best_match_value",
    "search_term",
    "best_match_id",
    "best_match_score",
]


@st.cache_resource(show_spinner="Loading Parquet dataset…")
def load_data(folder):
    """
    Load all Parquet files from a folder using pyarrow.dataset.
    """
    parquet_files = list(folder.glob("*.parquet"))
    dataset = ds.dataset(parquet_files, format="parquet")
    table = dataset.to_table(columns=REQUIRED_COLS)  # load only needed columns
    return table.to_pandas()


@st.cache_data(show_spinner="Condensing data…")
def condense_data(df):
    condensed = df.copy()

    condensed["Source_File"] = (
        condensed["Source_File"]
        .map(SOURCE_FILE_TEXT_MAP)
        .fillna(condensed["Source_File"])
    )
    return condensed


@st.cache_data(show_spinner="Computing chart…")
def make_match_bin_chart(condensed_df, selected_org):
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


def app():
    st.write("Preparing application…")

    input_data_dir = Path(__file__).parent.parent / "input_data" / "vs_tsvs"

    # ---- LOAD USING PYARROW ----
    df = load_data(input_data_dir)
    st.write(f"Loaded {len(df):,} rows.")

    condensed_df = condense_data(df)

    # -------------------
    # Organism selector
    # -------------------
    col1, col2 = st.columns([3, 1])

    with col2:
        organisms = sorted(condensed_df["Organism"].unique())
        selected_org = st.selectbox(
            "Select Organism", ["All"] + organisms, key="organism_select"
        )

    with col1:
        fig = make_match_bin_chart(condensed_df, selected_org)
        st.plotly_chart(fig, use_container_width=True)

    # -------------------
    # Sample table section
    # -------------------
    col1, col2 = st.columns([3, 1])

    with col2:
        sources = sorted(condensed_df["Source_File"].unique())
        selected_source = st.selectbox(
            "Select Source", ["All"] + sources, key="source_select"
        )

    with col1:
        sampled_df = sample_dataframe(condensed_df, selected_org, selected_source)
        st.write(
            f"Displaying {len(sampled_df)} records for Organism: {selected_org} "
            f"and Source: {selected_source}"
        )
        st.dataframe(sampled_df)


# app()
