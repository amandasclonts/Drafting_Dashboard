# =========================================
# IMPORT LIBRARIES
# =========================================

import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime


# =========================================
# PAGE SETTINGS
# =========================================

st.set_page_config(
    page_title="Drafting Hours Dashboard",
    layout="wide"
)

HISTORY_FILE = "drafting_hours_history.csv"

st.title("Drafting Hours Dashboard")


# =========================================
# FILE UPLOADER
# =========================================

uploaded_file = st.file_uploader(
    "Upload Weekly Drafting Hours Excel",
    type=["xls", "xlsx"]
)


# =========================================
# CREATE UNIQUE FILE HASH
# =========================================

def get_file_hash(file):
    file.seek(0)
    file_bytes = file.read()
    file.seek(0)
    return hashlib.md5(file_bytes).hexdigest()


# =========================================
# CLEAN EXCEL REPORT
# Works for reports where:
# - Date may be listed as a label row
# - Employee info is listed above detail rows
# - Hours / Cost Center columns may move
# =========================================

def clean_drafting_hours(uploaded_file):

    raw = pd.read_excel(uploaded_file, header=None)

    rows = []

    current_date = None
    employee_id = None
    first_name = None
    last_name = None

    hours_col = None
    job_col = None

    for _, row in raw.iterrows():

        col_a = row.iloc[0] if len(row) > 0 else None
        col_b = row.iloc[1] if len(row) > 1 else None

        # -----------------------------------------
        # Capture date from rows like:
        # Column A = Date, Column B = actual date
        # -----------------------------------------
        if col_a == "Date":
            current_date = pd.to_datetime(col_b, errors="coerce")

        # -----------------------------------------
        # Capture employee information
        # -----------------------------------------
        elif col_a == "Employee Id":
            employee_id = col_b

        elif col_a == "First Name":
            first_name = col_b

        elif col_a == "Last Name":
            last_name = col_b

        # -----------------------------------------
        # Find header row dynamically
        # This prevents the code from breaking if
        # Hours or Cost Center columns move.
        # -----------------------------------------
        elif "Hours Per Day" in row.values or "Hours" in row.values:

            if "Hours Per Day" in row.values:
                hours_col = row[row == "Hours Per Day"].index[0]
            elif "Hours" in row.values:
                hours_col = row[row == "Hours"].index[0]

            if "Cost Centers Full Path" in row.values:
                job_col = row[row == "Cost Centers Full Path"].index[0]
            elif "Cost Center Full Path" in row.values:
                job_col = row[row == "Cost Center Full Path"].index[0]
            elif "Full Job Path" in row.values:
                job_col = row[row == "Full Job Path"].index[0]

        # -----------------------------------------
        # Capture actual time entry rows
        # -----------------------------------------
        elif hours_col is not None and job_col is not None:

            hours_value = row.iloc[hours_col]
            job_value = row.iloc[job_col]

            if pd.notna(hours_value) and pd.notna(job_value):

                try:
                    hours = float(hours_value)
                except:
                    continue

                full_job_path = str(job_value).strip()

                if full_job_path.lower() in ["nan", ""]:
                    continue

                job_name = full_job_path.split("/")[0].strip()

                rows.append({
                    "Date": current_date,
                    "Employee ID": employee_id,
                    "Drafter": f"{first_name} {last_name}",
                    "Job": job_name,
                    "Full Job Path": full_job_path,
                    "Hours": hours
                })

    df = pd.DataFrame(rows)

    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Week"] = df["Date"].dt.to_period("W").astype(str)

        df = df.dropna(subset=["Date", "Drafter", "Job", "Hours"])

    return df


# =========================================
# LOAD HISTORICAL DATA
# =========================================

def load_history():

    if os.path.exists(HISTORY_FILE):

        df = pd.read_csv(HISTORY_FILE)

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        return df

    return pd.DataFrame()


# =========================================
# SAVE CURRENT UPLOAD TO HISTORY
# =========================================

def save_to_history(current_df, upload_id):

    history_df = load_history()

    current_df = current_df.copy()

    current_df["Upload ID"] = upload_id
    current_df["Uploaded At"] = datetime.now()

    combined = pd.concat([history_df, current_df], ignore_index=True)

    combined = combined.drop_duplicates(
        subset=[
            "Date",
            "Employee ID",
            "Drafter",
            "Job",
            "Full Job Path",
            "Hours"
        ],
        keep="first"
    )

    combined.to_csv(HISTORY_FILE, index=False)

    return combined


# =========================================
# DASHBOARD FUNCTION
# =========================================

def show_dashboard(df, title):

    st.subheader(title)

    if df.empty:
        st.info("No data available yet.")
        return

    df = df.copy()

    # -----------------------------------------
    # Optional filters
    # -----------------------------------------
    include_office = st.checkbox(
        f"Include Office hours - {title}",
        value=True
    )

    if not include_office:
        df = df[df["Job"].str.lower() != "office"]

    if df.empty:
        st.warning("No data after filters.")
        return

    # -----------------------------------------
    # Sidebar-style filters inside each tab
    # -----------------------------------------
    with st.expander("Filters", expanded=False):

        weeks = sorted(df["Week"].dropna().unique())
        selected_weeks = st.multiselect(
            f"Week - {title}",
            weeks,
            default=weeks
        )

        drafters = sorted(df["Drafter"].dropna().unique())
        selected_drafters = st.multiselect(
            f"Drafter - {title}",
            drafters,
            default=drafters
        )

        jobs = sorted(df["Job"].dropna().unique())
        selected_jobs = st.multiselect(
            f"Job - {title}",
            jobs,
            default=jobs
        )

    df = df[
        (df["Week"].isin(selected_weeks)) &
        (df["Drafter"].isin(selected_drafters)) &
        (df["Job"].isin(selected_jobs))
    ]

    if df.empty:
        st.warning("No data after filters.")
        return

    # -----------------------------------------
    # Top metrics
    # -----------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    total_hours = df["Hours"].sum()
    total_drafters = df["Drafter"].nunique()
    total_jobs = df["Job"].nunique()

    top_drafter = (
        df.groupby("Drafter")["Hours"]
        .sum()
        .idxmax()
    )

    col1.metric("Total Hours", round(total_hours, 2))
    col2.metric("Drafters", total_drafters)
    col3.metric("Jobs Worked On", total_jobs)
    col4.metric("Highest Hours Drafter", top_drafter)

    # -----------------------------------------
    # Hours by drafter chart
    # -----------------------------------------
    st.subheader("Hours by Drafter")

    drafter_chart = (
        df.groupby("Drafter")["Hours"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(drafter_chart)

    # -----------------------------------------
    # Hours by job chart
    # -----------------------------------------
    st.subheader("Hours by Job")

    job_chart = (
        df.groupby("Job")["Hours"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(job_chart)

    # -----------------------------------------
    # Drafter workload summary
    # -----------------------------------------
    st.subheader("Drafter Workload Summary")

    summary = (
        df.groupby("Drafter")
        .agg(
            Total_Hours=("Hours", "sum"),
            Jobs_Worked=("Job", "nunique")
        )
        .reset_index()
        .sort_values("Total_Hours", ascending=False)
    )

    jobs = (
        df.groupby("Drafter")["Job"]
        .apply(lambda x: ", ".join(sorted(x.dropna().unique())))
        .reset_index(name="Jobs")
    )

    summary = summary.merge(jobs, on="Drafter", how="left")

    st.dataframe(summary, use_container_width=True)

    # -----------------------------------------
    # Job breakdown table
    # -----------------------------------------
    st.subheader("Job Breakdown by Drafter")

    job_breakdown = (
        df.groupby(["Job", "Drafter"])["Hours"]
        .sum()
        .reset_index()
        .sort_values(["Job", "Hours"], ascending=[True, False])
    )

    st.dataframe(job_breakdown, use_container_width=True)

    # -----------------------------------------
    # Detailed log
    # -----------------------------------------
    st.subheader("Detailed Hours Log")

    st.dataframe(df, use_container_width=True)


# =========================================
# MAIN APP LOGIC
# =========================================

current_df = pd.DataFrame()
history_df = load_history()

if uploaded_file:

    upload_id = get_file_hash(uploaded_file)

    current_df = clean_drafting_hours(uploaded_file)

    if current_df.empty:
        st.error("No usable data found in this Excel file.")

        st.info(
            "This usually means the report format changed or the expected "
            "headers like 'Hours Per Day' and 'Cost Centers Full Path' were not found."
        )

    else:
        st.success("Current file loaded successfully!")

        if st.button("Save Current Upload to Historical Data"):
            history_df = save_to_history(current_df, upload_id)
            st.success("Saved to historical data.")


# =========================================
# CREATE DASHBOARD TABS
# =========================================

tab1, tab2 = st.tabs([
    "Current Upload",
    "Current + Historical Data"
])


# =========================================
# TAB 1: CURRENT UPLOAD ONLY
# =========================================

with tab1:
    show_dashboard(
        current_df,
        "Current Upload"
    )


# =========================================
# TAB 2: CURRENT + HISTORICAL DATA
# =========================================

with tab2:

    if not current_df.empty:

        combined_df = pd.concat(
            [history_df, current_df],
            ignore_index=True
        )

        combined_df = combined_df.drop_duplicates(
            subset=[
                "Date",
                "Employee ID",
                "Drafter",
                "Job",
                "Full Job Path",
                "Hours"
            ],
            keep="first"
        )

    else:
        combined_df = history_df

    show_dashboard(
        combined_df,
        "Current + Historical Data"
    )
