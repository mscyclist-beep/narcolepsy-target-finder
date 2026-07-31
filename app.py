import pandas as pd
import streamlit as st

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
def center_narcolepsy_score(row):
    score = 0

    # Core narcolepsy signals
    if row.get("Treats_Narcolepsy", False):
        score += 3

    # Practice type weighting
    if row.get("Practice_Type") == "Sleep Medicine":
        score += 3
    elif row.get("Practice_Type") == "Neurology / Sleep":
        score += 2
    elif row.get("Practice_Type") == "Pulmonary / Sleep":
        score += 1

    # PSG / MSLT capability (if these columns exist in your centers data)
    if row.get("Does_PSG", False):
        score += 1
    if row.get("Does_MSLT", False):
        score += 2

    # Hypersomnia / narcolepsy focus flag
    if row.get("Hypersomnia_Focus", False) or row.get("Narcolepsy_Focus", False):
        score += 1

    # Sleep fellowship / board certification at the center level (if tracked)
    if row.get("Has_Sleep_Fellowship_Staff", False) or row.get("Has_Sleep_Boarded_Staff", False):
        score += 1

    # Important: we do NOT subtract points for apnea-heavy volume here
    # Apnea volume is not used as a negative in this narcolepsy-focused score.

    return score

centers["Narcolepsy_Score"] = centers.apply(center_narcolepsy_score, axis=1)
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
state_list = state_options
selected_state = st.sidebar.selectbox("State", state_list)
county_options = sorted(
    counties[counties["State"] == selected_state]["County"].unique()
)
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
with st.expander("How this Narcolepsy NT1 Target Finder works", expanded=True):
    st.markdown("""
### 1. What this tool shows

- This tool helps you find **sleep centers and clinicians** in Tennessee, Kentucky, and Indiana who are likely to diagnose and treat **narcolepsy type 1 (NT1)**.
- You pick a **State**, **County**, and **Practice Type** on the left.
- The app then shows:
  - The **county population**
  - The **estimated number of NT1 patients in that county**
  - **Ranked sleep centers** and **ranked HCPs** for that territory

### 2. Where the county numbers come from

- We load a file called **"Counties Narcolepsy - TN_KY_IN.csv"**.
- For each county, this file includes:
  - County name
  - State (Tennessee, Kentucky, or Indiana)
  - Population (from public census-style data)
  - An NT1 estimate (NT1_Est)

### 3. How we estimate NT1 patients (NT1_Est)

- NT1_Est is our **estimated number of NT1 patients** in that county.
- We use this simple formula:

  NT1_Est = Population × 0.0126%

- The 0.0126% number comes from published research that found about **0.0126% of people have NT1** (about 1 person out of every 7,900 people in the population).
- These are **planning estimates**, not actual diagnosed patient counts.

### 4. How the State and County dropdowns work

- The **State** dropdown is built from all distinct states in the county file (Tennessee, Kentucky, Indiana).
- Once you pick a state, the **County** dropdown only shows counties in that state from the same file.
- This means:
  - If you pick Tennessee, you only see Tennessee counties.
  - If you pick Kentucky, you only see Kentucky counties.
  - If you pick Indiana, you only see Indiana counties.

### 5. Practice Type categories

- Practice Type lets you filter by the **type of practice**:
  - **All Non-Apnea** – Sleep Medicine, Neurology / Sleep, and selected Pulmonology / Sleep
  - **Sleep Medicine** – practices focused on sleep across many conditions
  - **Neurology / Sleep** – neurologists with a sleep focus
  - **Pulmonary / Sleep** – pulmonology-based sleep practices
  - **Apnea-Heavy (Asteroid Group)** – centers that are mostly apnea-focused, with limited public narcolepsy focus
- These categories help us **prioritize narcolepsy-focused work**, but they do **not** automatically exclude any clinician from the data.

### 6. What makes a site or HCP "narcolepsy-relevant"

- We give more weight to:
  - **Sleep Medicine** and **Neurology / Sleep** clinicians
  - Centers that perform **overnight sleep studies (PSG)** and **Multiple Sleep Latency Tests (MSLT)**, which are standard tests used to diagnose narcolepsy
  - Centers and clinicians that list **hypersomnia or narcolepsy** as a focus
- We do **not** penalize high apnea volume:
  - A site can do a lot of apnea studies and still score high if it also does PSG + MSLT and sees hypersomnia/narcolepsy patients.

### 7. Training and credentials

- We only include clinicians with these credentials:
  - **MD**, **DO**, **PA**, **NP**
- If we know that a clinician has:
  - A **sleep fellowship**
  - Or **board certification in Sleep Medicine**
- Then we may give them a **small score bonus**, but this is a **nice-to-have**:
  - It does **not** automatically qualify or disqualify anyone.

### 8. Sunshine / Open Payments and speaker fees

- We include only **non-meal, non–food and beverage** payments when we look at engagement:
  - Examples: consulting, speaking, CME, grants, education.
- These payments are used as a **light weight** in scores to reflect real-world engagement.
- We do **not** use speaker fees as a strict filter:
  - They can adjust the rank slightly.
  - They do not remove someone from the list.

### 9. How to read the outputs

- **County population and NT1 estimate**:
  - Population = total people in that county.
  - NT1_Est = estimated NT1 patients in that county using the 0.0126% rate.
- **Top Sleep Centers** table:
  - Shows centers in the selected state and county.
  - Sorted by an internal "Center Score" that reflects:
    - Practice type
    - PSG + MSLT capability
    - Hypersomnia / narcolepsy focus
    - Credentials and accreditation
- **Top HCPs** table:
  - Shows clinicians in that territory.
  - Sorted by "HCP Score", which combines:
    - Specialty and practice type
    - Narcolepsy / hypersomnia signals
    - Training and engagement signals

### 10. Important reminder

- This tool is meant to **support planning and targeting**.
- It does **not** replace:
  - Clinical judgment
  - Local field insights
  - Final medical decision making
    """)
