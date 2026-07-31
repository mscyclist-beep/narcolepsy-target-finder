import pandas as pd
import streamlit as st
# Let the user pick a state
state_options = sorted(counties["State"].unique())
selected_state = st.selectbox("State", state_options)

# Let the user pick a county within that state
county_options = sorted(
    counties.loc[counties["State"] == selected_state, "County"].unique()
)
selected_county = st.selectbox("County", county_options)
st.set_page_config(page_title="Narcolepsy NT1 Target Finder – TN, KY, IN", layout="wide")

st.title("Narcolepsy NT1 Target Finder")
st.caption("Tennessee, Kentucky, Indiana – public-data-based territory targeting")

# Load TN, KY, IN counties with population and NT1 estimates

# Load TN, KY, IN counties with population and NT1 estimates
counties = pd.read_csv("Counties Narcolepsy - TN_KY_IN.csv")# Limit to Tennessee, Kentucky, and Indiana only
counties = counties[counties["State"].isin(["Tennessee", "Kentucky", "Indiana"])]

# Let the user pick a state and county
state_options = sorted(counties["State"].unique())
selected_state = st.selectbox("Select state", state_options)

county_options = sorted(counties[counties["State"] == selected_state]["County"].unique())
selected_county = st.selectbox("Select county", county_options)

# Show population and NT1 estimate for that county
selected_county_data = counties[
    (counties["State"] == selected_state) &
    (counties["County"] == selected_county)
]

st.write("County population and NT1 estimate:")
st.write(selected_county_data[["Population", "NT1_Est"]])

st.write("County population and NT1 estimate:")
st.write(selected_county_data[["Population", "NT1_Est"]])
# Limit to Tennessee, Kentucky, and Indiana only
counties = counties[counties["State"].isin(["Tennessee", "Kentucky", "Indiana"])]

# Show population and NT1 estimate for that county
selected_county_data = counties[
    (counties["State"] == selected_state) &
    (counties["County"] == selected_county)
]

st.write("County population and NT1 estimate:")
st.write("County population and NT1 estimate:")

st.write(selected_county_data[["Population", "NT1_Est"]])
ALLOWED_TN_COUNTIES = [
    "Williamson", "Davidson", "Rutherford", "Robertson",
    "Hamilton"  # Hamilton kept only if within allowed launch footprint; adjust as needed
]

@st.cache_data
def load_data():
    try:
        centers = pd.read_csv("centers.csv")
        hcps = pd.read_csv("hcps.csv")
        counties = pd.read_csv("Counties Narcolepsy - TN_KY_IN.csv")
    except FileNotFoundError:
        st.error("centers.csv and hcps.csv must be in the same folder as app.py")
        st.stop()
    return centers, hcps, counties

centers, hcps, counties = load_data()

# Apply geography rule: only TN/KY/IN, and TN restricted to allowed counties
def apply_geo_filter(df):
    df = df[df["State"].isin(["Tennessee", "Kentucky", "Indiana"])]
    tn_mask = (df["State"] == "Tennessee") & (~df["County"].isin(ALLOWED_TN_COUNTIES))
    df = df[~tn_mask]
    return df

centers = apply_geo_filter(centers)
hcps = apply_geo_filter(hcps)

# Credential filter
hcps = hcps[hcps["Credentials"].isin(["MD", "DO", "PA", "NP"])]

# Asteroid flag
centers["Asteroid"] = (centers["Sleep_Apnea_Heavy"] == True) & (centers["Treats_Narcolepsy"] == False)
hcps["Asteroid"] = (hcps["Sleep_Apnea_Heavy"] == True) & (hcps["Treats_Narcolepsy"] == False)

# Center score
def center_score(row):
    score = 0
    if row["Treats_Narcolepsy"]: score += 2
    if row["AASM_Accredited"]: score += 2
    if row["Regional_Sleep_Program"]: score += 1
    if not row["Sleep_Apnea_Heavy"]: score += 1
    return score

centers["Center_Score"] = centers.apply(center_score, axis=1)

center_score_map = centers.set_index("Center_ID")["Center_Score"].to_dict()

def sponsorship_score(events):
    if events >= 5: return 2
    if events >= 1: return 1
    return 0

def hcp_score(row):
    score = 0
    if row["Treats_Narcolepsy"]: score += 2
    if row["Specialty"] in ["Sleep Medicine", "Neurology / Sleep", "Pulmonary / Sleep"]: score += 1
    c_score = center_score_map.get(row["Center_ID"], 0)
    if c_score >= 3: score += 1
    if row["Credentials"] in ["MD", "DO"]: score += 1
    score += sponsorship_score(row.get("Sunshine_Total_Sponsorship_Events", 0))
    return score

hcps["HCP_Score"] = hcps.apply(hcp_score, axis=1)

# Sidebar
st.sidebar.header("Territory Selection")
state_list = ["Tennessee", "Kentucky", "Indiana"]
selected_state = st.sidebar.selectbox("State", state_list)

county_options = sorted(centers[centers["State"] == selected_state]["County"].unique())
selected_county = st.sidebar.selectbox("County", county_options)

practice_options = ["All Non-Apnea", "Sleep Medicine", "Neurology / Sleep", "Pulmonary / Sleep", "Apnea-Heavy (Asteroid Group)"]
selected_practice = st.sidebar.selectbox("Practice Type", practice_options)

generate = st.sidebar.button("Generate Targets")

if generate:
    c_filtered = centers[
        (centers["State"] == selected_state) &
        (centers["County"] == selected_county) &
        (centers["Asteroid"] == False)
    ].sort_values("Center_Score", ascending=False)

    st.subheader("Top Sleep Centers — Narcolepsy NT1 Focus")
    if not c_filtered.empty:
        st.dataframe(
            c_filtered[["Center_Name","Facility_System","City","County","State","ZIP",
                        "AASM_Accredited","Treats_Narcolepsy","Regional_Sleep_Program","Center_Score"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.warning("No qualifying sleep centers found for this county.")

    h_filtered = hcps[
        (hcps["State"] == selected_state) &
        (hcps["County"] == selected_county) &
        (hcps["Asteroid"] == False)
    ]

    if selected_practice == "All Non-Apnea":
        pass
    elif selected_practice == "Apnea-Heavy (Asteroid Group)":
        h_filtered = hcps[
            (hcps["State"] == selected_state) &
            (hcps["County"] == selected_county) &
            (hcps["Asteroid"] == True)
        ]
    else:
        h_filtered = h_filtered[h_filtered["Specialty"] == selected_practice]

    h_filtered = h_filtered.sort_values("HCP_Score", ascending=False).head(10)
    h_filtered = h_filtered.copy()
    h_filtered.insert(0, "Rank", range(1, len(h_filtered) + 1))
    h_filtered["HCP"] = h_filtered["HCP_Name"] + ", " + h_filtered["Credentials"]

    st.subheader("Top 10 HCPs — MD / DO / PA / NP")
    if not h_filtered.empty:
        st.dataframe(
            h_filtered[["Rank","HCP","Specialty","Center_Name","City","County","State","ZIP","HCP_Score"]],
            use_container_width=True, hide_index=True
        )
        csv_data = h_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("Export Target List to CSV", csv_data,
                            file_name=f"Narcolepsy_Targets_{selected_state}_{selected_county}.csv",
                            mime="text/csv")
    else:
        st.warning("No matching HCPs found for this selection.")

    with st.expander("Apnea-only / Low-priority centers (Asteroid group)"):
        asteroid_centers = centers[
            (centers["State"] == selected_state) &
            (centers["County"] == selected_county) &
            (centers["Asteroid"] == True)
        ]
        if not asteroid_centers.empty:
            st.dataframe(
                asteroid_centers[["Center_Name","Facility_System","City","County","State","ZIP"]],
                use_container_width=True, hide_index=True
            )
        else:
            st.write("None found for this county.")
else:
    st.info("Select State, County, and Practice Type in the sidebar, then click Generate Targets.")
    
with st.expander("How these estimates and scores were calculated", expanded=True):
    st.markdown("""
- **Population** comes from publicly available county-level census data.
- **NT1_Est** = Population × 0.0126%.
  - 0.0126% is a published estimate of NT1 prevalence in the US population.
- These estimates are for planning only and do not represent diagnosed patients.
- **Practice Type** filters providers by specialty (for example, Sleep Medicine or Neurology).
- **HCP scores** rank providers using factors like specialty, role, and center affiliation.
    """)
