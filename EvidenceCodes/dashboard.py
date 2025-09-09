# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

EVIDENCE_CODE_DESCRIPTIONS = {
    # Experimental
    "EXP": "Inferred from Experiment",
    "IDA": "Inferred from Direct Assay",
    "IPI": "Inferred from Physical Interaction",
    "IMP": "Inferred from Mutant Phenotype",
    "IGI": "Inferred from Genetic Interaction",
    "IEP": "Inferred from Expression Pattern",
    # High Throughput
    "HTP": "Inferred from High Throughput Experiment",
    "HDA": "Inferred from High Throughput Direct Assay",
    "HMP": "Inferred from High Throughput Mutant Phenotype",
    "HGI": "Inferred from High Throughput Genetic Interaction",
    "HEP": "Inferred from High Throughput Expression Pattern",
    # Phylogenetic
    "IBA": "Inferred from Biological aspect of Ancestor",
    "IBD": "Inferred from Biological aspect of Descendant",
    "IKR": "Inferred from Key Residues",
    "IRD": "Inferred from Rapid Divergence",
    # Computational
    "ISS": "Inferred from Sequence or structural Similarity",
    "ISO": "Inferred from Sequence Orthology",
    "ISA": "Inferred from Sequence Alignment",
    "ISM": "Inferred from Sequence Model",
    "IGC": "Inferred from Genomic Context",
    "RCA": "Inferred from Reviewed Computational Analysis",
    "IEA": "Inferred from Electronic Annotation",
    # Author statements
    "TAS": "Traceable Author Statement",
    "NAS": "Non-traceable Author Statement",
    # Curator statements
    "IC": "Inferred by Curator",
    "ND": "No biological Data available",
}

EVIDENCE_CATERGORIES = {
    "EXP": "Experimental",
    "IDA": "Experimental",
    "IPI": "Experimental",
    "IMP": "Experimental",
    "IGI": "Experimental",
    "IEP": "Experimental",
    "HTP": "High Throughput",
    "HDA": "High Throughput",
    "HMP": "High Throughput",
    "HGI": "High Throughput",
    "HEP": "High Throughput",
    "IBA": "Phylogenetic",
    "IBD": "Phylogenetic",
    "IKR": "Phylogenetic",
    "IRD": "Phylogenetic",
    "ISS": "Computational",
    "ISO": "Computational",
    "ISA": "Computational",
    "ISM": "Computational",
    "IGC": "Computational",
    "RCA": "Computational",
    "TAS": "Author statements",
    "NAS": "Author statements",
    "IC": "Curator statements",
    "ND": "Curator statements",
    "IEA": "Computational",
}


def app():
    """
    Main function to render the Streamlit dashboard.
    """
    # Example data and plots can be replaced with actual data and visualizations

    # ---- PAGE CONFIG ----
    st.set_page_config(page_title="Evidence Code Plots", layout="wide")

    # ---- TITLE ----
    st.title("Evidence Code distribution")

    # ---- SUMMARY TABLE ----
    st.subheader("Summary Table")

    # get this python file's directory
    input_data_dir = Path(__file__).parent.parent.joinpath("input_data")
    input_file = input_data_dir.joinpath("evidence_codes_No_Alternate.parquet")
    df = pd.read_parquet(input_file)

    summary_df = df["Evidence Code"].value_counts().reset_index()
    summary_df.columns = ["Evidence Code", "Count"]
    summary_df["Description"] = summary_df["Evidence Code"].map(
        EVIDENCE_CODE_DESCRIPTIONS
    )
    summary_df = summary_df[["Evidence Code", "Description", "Count"]]
    # addnew row at the bottom for total NA
    total_na = df["Evidence Code"].isna().sum()
    summary_df = pd.concat(
        [
            summary_df,
            pd.DataFrame(
                [["NA", "No Evidence Code", total_na]],
                columns=["Evidence Code", "Description", "Count"],
            ),
        ],
        ignore_index=True,
    )
    st.dataframe(summary_df, width="stretch")

    df = df[
        [
            "Gene ID",
            "Evidence Code",
            "Assigned By",
            "Organism",
            "is_uninformative_name",
            "Project",
        ]
    ]
    # remove na

    df["Evidence_group"] = df["Evidence Code"].map(EVIDENCE_CATERGORIES)
    evidence_group_counts = df["Evidence_group"].value_counts().reset_index()
    evidence_group_counts.columns = ["Evidence Group", "Count"]
    # Create two columns
    df = df.fillna(
        {
            "Organism": "Unknown",
            "Evidence_group": "NA",
            "Evidence Code": "NA",
            # "is_uniformative_name": "Unknown",
        }
    )
    col1, col2 = st.columns(2)

    # Display the table in the first column
    with col1:
        st.subheader("Evidence Code Group distribution")
        st.dataframe(evidence_group_counts, width="content")

    # Display the chart in the second column
    with col2:
        fig = px.pie(
            evidence_group_counts,
            names="Evidence Group",
            values="Count",
            title="Evidence Code Group Distribution",
        )
        st.plotly_chart(fig, width="stretch")

    # Sunburst chart
    st.subheader("Evidence Code Sunburst Chart")

    def make_sunburst(selected_org=None):
        # Filter df if organism is selected
        if selected_org and selected_org != "All":
            df_sub = df[df["Organism"] == selected_org].copy()
        else:
            df_sub = df.copy()

        fig = px.sunburst(
            df_sub,
            path=[
                "Project",
                "Organism",
                "Evidence_group",
                "Evidence Code",
                "is_uninformative_name",
            ],
            title="Evidence Code Sunburst Chart",
        )

        fig.update_layout(
            margin=dict(t=50, l=0, r=0, b=0),
            autosize=True,
            width=900,
            height=900,
        )

        return fig

    col1, col2 = st.columns([3, 1])

    with col2:
        organisms = ["All"] + sorted(df["Organism"].unique().tolist())
        selected_org = st.selectbox("Jump to Organism", organisms)

        st.markdown("### Ring Key")
        st.markdown(
            """
        - **1st ring** → Project (Database)  
        - **2nd ring** → Organism  
        - **3rd ring** → Evidence Group  (NA if Evidence Code is missing)  
        - **4th ring** → Evidence Code (NA if missing)  
        - **5th ring** → Informative Name Flag (False = Informative, True = Uninformative)  
        """
        )

    with col1:
        fig2 = make_sunburst(selected_org)
        st.plotly_chart(fig2, use_container_width=True)

    st.caption(
        "Note: Hover over the sections to see details. Click on sections to zoom in."
        " Double-click to zoom out. Press the fullscreen button for a better view."
        " If using the 'Jump to Organism' dropdown, please select 'All' to reset the view."
        " The allows for navigation using click and zoom controls."
    )


def load_data(file_path):
    """
    Load data from a CSV or Parquet file.
    Args:
        file_path (str): Path to the data file.
    Returns:

        pd.DataFrame: Loaded data as a pandas DataFrame.
    """
    try:
        if file_path.endswith(".csv"):
            return pd.read_csv(file_path)
        elif file_path.endswith(".parquet"):
            return pd.read_parquet(file_path)
        else:
            st.error("Unsupported file format. Please upload a CSV or Parquet file.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
