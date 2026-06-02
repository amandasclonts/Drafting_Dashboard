# =========================================
# IMPORT LIBRARIES
# =========================================

# Streamlit = web app framework
import streamlit as st

# Pandas = data cleaning / tables / grouping
import pandas as pd

# os = check if history file exists
import os

# hashlib = creates unique ID for uploaded files
import hashlib

# datetime = timestamp when uploads are saved
from datetime import datetime

# =========================================
# PAGE SETTINGS
# =========================================

# Sets browser tab title and wide layout
st.set_page_config(
    page_title="Drafting Hours Dashboard",
    layout="wide"
)

# Historical data file name
# This CSV stores ALL previous uploads
HISTORY_FILE = "drafting_hours_history.csv"

# Dashboard title
st.title("Drafting Hours Dashboard")

# =========================================
# FILE UPLOADER
# =========================================

# Creates upload button at top of app
uploaded_file = st.file_uploader(
    "Upload Weekly Drafting Hours Excel",
    type=["xls", "xlsx"]
)

# =========================================
# CREATE UNIQUE FILE HASH
# =========================================

# This helps prevent duplicate uploads
def get_file_hash(file):

    # Reset file position
    file.seek(0)

    # Read all bytes
    file_bytes = file.read()

    # Reset again so pandas can read later
    file.seek(0)

    # Create unique MD5 hash
    return hashlib.md5(file_bytes).hexdigest()

# =========================================
# CLEAN THE EXCEL REPORT
# =========================================

def clean_drafting_hours(uploaded_file):

    # Read Excel with NO headers
    # We do this because the report format is messy
    raw = pd.read_excel(uploaded_file, header=None)

    # Empty list to store cleaned rows
    rows = []

    # Variables that hold current employee info
    employee_id = None
    first_name = None
    last_name = None

    # Loop through every row in Excel
    for _, row in raw.iterrows():

        # Grab important columns
        col_a = row.iloc[0] if len(row) > 0 else None
        col_b = row.iloc[1] if len(row) > 1 else None
        col_i = row.iloc[8] if len(row) > 8 else None

        # =========================================
        # FIND EMPLOYEE INFORMATION
        # =========================================

        # Employee ID row
        if col_a == "Employee Id":
            employee_id = col_b

        # First Name row
        elif col_a == "First Name":
            first_name = col_b

        # Last Name row
        elif col_a == "Last Name":
            last_name = col_b

        # =========================================
        # FIND ACTUAL TIME ENTRY ROWS
        # =========================================

        else:

            # Try converting column A into a date
            date_value = pd.to_datetime(col_a, errors="coerce")

            # Valid row requirements:
            # - valid date
            # - hours exists
            # - job path exists
            if pd.notna(date_value) and pd.notna(col_b) and pd.notna(col_i):

                # Convert hours into number
                try:
                    hours = float(col_b)

                # Skip invalid rows
                except:
                    continue

                # Full job/cost center path
                full_job_path = str(col_i).strip()

                # Extract main job name
                # Example:
                # "12345 / ABC Job / Drafting"
                # becomes:
                # "12345"
                job_name = full_job_path.split("/")[0].strip()

                # Add cleaned row into list
                rows.append({

                    # Work date
                    "Date": date_value,

                    # Employee ID
                    "Employee ID": employee_id,

                    # Full drafter name
                    "Drafter": f"{first_name} {last_name}",

                    # Main job
                    "Job": job_name,

                    # Full cost center path
                    "Full Job Path": full_job_path,

                    # Hours worked
                    "Hours": hours
                })

    # Convert list into dataframe
    df = pd.DataFrame(rows)

    # =========================================
    # CREATE WEEK COLUMN
    # =========================================

    if not df.empty:

        # Converts dates into week periods
        # Example:
        # 2026-05-09 -> 2026-05-04/2026-05-10
        df["Week"] = df["Date"].dt.to_period("W").astype(str)

    return df

# =========================================
# LOAD HISTORICAL DATA
# =========================================

def load_history():

    # Check if history CSV exists
    if os.path.exists(HISTORY_FILE):

        # Read CSV
        df = pd.read_csv(HISTORY_FILE)

        # Convert Date column back into datetime
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        return df

    # Return empty dataframe if no history yet
    return pd.DataFrame()

# =========================================
# SAVE CURRENT DATA TO HISTORY
# =========================================

def save_to_history(current_df, upload_id):

    # Load old history
    history_df = load_history()

    # Copy current dataframe
    current_df = current_df.copy()

    # Add upload metadata
    current_df["Upload ID"] = upload_id
    current_df["Uploaded At"] = datetime.now()

    # Combine old + new data
    combined = pd.concat([history_df, current_df], ignore_index=True)

    # =========================================
    # REMOVE DUPLICATES
    # =========================================

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

    # Save combined history back to CSV
    combined.to_csv(HISTORY_FILE, index=False)

    return combined

# =========================================
# DASHBOARD DISPLAY FUNCTION
# =========================================

def show_dashboard(df, title):

    # Section title
    st.subheader(title)

    # If no data exists
    if df.empty:
        st.info("No data available yet.")
        return

    # =========================================
    # OFFICE FILTER
    # =========================================

    include_office = st.checkbox(
        f"Include Office hours - {title}",
        value=True
    )

    # Remove office rows if unchecked
    if not include_office:
        df = df[df["Job"].str.lower() != "office"]

    # =========================================
    # TOP METRICS
    # =========================================

    col1, col2, col3, col4 = st.columns(4)

    # Calculate metrics
    total_hours = df["Hours"].sum()
    total_drafters = df["Drafter"].nunique()
    total_jobs = df["Job"].nunique()

    # Find drafter with most hours
    top_drafter = (
        df.groupby("Drafter")["Hours"]
        .sum()
        .idxmax()
        if not df.empty else "N/A"
    )

    # Display metrics
    col1.metric("Total Hours", round(total_hours, 2))
    col2.metric("Drafters", total_drafters)
    col3.metric("Jobs Worked On", total_jobs)
    col4.metric("Highest Hours Drafter", top_drafter)

    # =========================================
    # HOURS BY DRAFTER CHART
    # =========================================

    st.subheader("Hours by Drafter")

    drafter_chart = (
        df.groupby("Drafter")["Hours"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(drafter_chart)

    # =========================================
    # HOURS BY JOB CHART
    # =========================================

    st.subheader("Hours by Job")

    job_chart = (
        df.groupby("Job")["Hours"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(job_chart)

    # =========================================
    # DRAFTER SUMMARY TABLE
    # =========================================

    st.subheader("Drafter Workload Summary")

    # Summary calculations
    summary = (
        df.groupby("Drafter")
        .agg(
            Total_Hours=("Hours", "sum"),
            Jobs_Worked=("Job", "nunique")
        )
        .reset_index()
    )

    # Combine all jobs worked into one string
    jobs = (
        df.groupby("Drafter")["Job"]
        .apply(lambda x: ", ".join(sorted(x.dropna().unique())))
        .reset_index(name="Jobs")
    )

    # Merge summary + jobs list
    summary = summary.merge(jobs, on="Drafter", how="left")

    # Display summary table
    st.dataframe(summary, use_container_width=True)

    # =========================================
    # JOB BREAKDOWN TABLE
    # =========================================

    st.subheader("Job Breakdown by Drafter")

    job_breakdown = (
        df.groupby(["Job", "Drafter"])["Hours"]
        .sum()
        .reset_index()
        .sort_values(["Job", "Hours"], ascending=[True, False])
    )

    st.dataframe(job_breakdown, use_container_width=True)

    # =========================================
    # DETAILED LOG TABLE
    # =========================================

    st.subheader("Detailed Hours Log")

    st.dataframe(df, use_container_width=True)

# =========================================
# MAIN APP LOGIC
# =========================================

# Empty dataframe for current upload
current_df = pd.DataFrame()

# Load historical data
history_df = load_history()

# =========================================
# HANDLE FILE UPLOAD
# =========================================

if uploaded_file:

    # Generate unique upload ID
    upload_id = get_file_hash(uploaded_file)

    # Clean uploaded report
    current_df = clean_drafting_hours(uploaded_file)

    # If no usable data found
    if current_df.empty:
        st.error("No usable data found in this Excel file.")

    else:

        # Success message
        st.success("Current file loaded successfully!")

        # Save button
        if st.button("Save Current Upload to Historical Data"):

            # Save current upload into history CSV
            history_df = save_to_history(current_df, upload_id)

            st.success("Saved to historical data.")

# =========================================
# CREATE TABS
# =========================================

tab1, tab2 = st.tabs([
    "Current Upload",
    "Current + Historical Data"
])

# =========================================
# TAB 1 = CURRENT UPLOAD ONLY
# =========================================

with tab1:

    show_dashboard(
        current_df,
        "Current Upload"
    )

# =========================================
# TAB 2 = CURRENT + HISTORY
# =========================================

with tab2:

    # If current upload exists
    if not current_df.empty:

        # Combine history + current upload
        combined_df = pd.concat(
            [history_df, current_df],
            ignore_index=True
        )

        # Remove duplicates
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

    # Otherwise only show history
    else:
        combined_df = history_df

    # Show dashboard
    show_dashboard(
        combined_df,
        "Current + Historical Data"
    )