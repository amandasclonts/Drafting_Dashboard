import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime

st.set_page_config(page_title="Drafting Hours Dashboard", layout="wide")

HISTORY_FILE = "drafting_hours_history.csv"

st.title("Drafting Hours Dashboard")

uploaded_file = st.file_uploader(
    "Upload Weekly Drafting Hours Excel",
    type=["xls", "xlsx"]
)


def get_file_hash(file):
    file.seek(0)
    file_bytes = file.read()
    file.seek(0)
    return hashlib.md5(file_bytes).hexdigest()


def clean_drafting_hours(uploaded_file):
    raw = pd.read_excel(uploaded_file, header=None)

    rows = []

    current_date = None
    employee_id = None
    first_name = None
    last_name = None

    date_col = None
    hours_col = None
    job_col = None

    for _, row in raw.iterrows():

        values = [str(v).strip() if pd.notna(v) else "" for v in row.values]

        col_a = row.iloc[0] if len(row) > 0 else None
        col_b = row.iloc[1] if len(row) > 1 else None

        # -----------------------------
        # Capture grouped date format
        # Example:
        # Column A = Date
        # Column B = 05/25/2026
        # -----------------------------
        if str(col_a).strip() == "Date" and pd.notna(col_b):
            current_date = pd.to_datetime(col_b, errors="coerce")

        # -----------------------------
        # Capture employee info
        # -----------------------------
        elif str(col_a).strip() == "Employee Id":
            employee_id = col_b

        elif str(col_a).strip() == "First Name":
            first_name = col_b

        elif str(col_a).strip() == "Last Name":
            last_name = col_b

        # -----------------------------
        # Find header row dynamically
        # This works for both report types
        # -----------------------------
        elif (
            "Hours Per Day" in values
            or "Total Hours" in values
            or "Hours" in values
        ) and (
            "Cost Centers Full Path" in values
            or "Cost Center Full Path" in values
            or "Full Job Path" in values
        ):

            # Reset columns for each new block
            date_col = None
            hours_col = None
            job_col = None

            if "Date" in values:
                date_col = values.index("Date")

            if "Hours Per Day" in values:
                hours_col = values.index("Hours Per Day")
            elif "Total Hours" in values:
                hours_col = values.index("Total Hours")
            elif "Hours" in values:
                hours_col = values.index("Hours")

            if "Cost Centers Full Path" in values:
                job_col = values.index("Cost Centers Full Path")
            elif "Cost Center Full Path" in values:
                job_col = values.index("Cost Center Full Path")
            elif "Full Job Path" in values:
                job_col = values.index("Full Job Path")

        # -----------------------------
        # Capture actual time rows
        # -----------------------------
        elif hours_col is not None and job_col is not None:

            hours_value = row.iloc[hours_col] if hours_col < len(row) else None
            job_value = row.iloc[job_col] if job_col < len(row) else None

            # Some reports have date in each detail row
            if date_col is not None and date_col < len(row):
                row_date = pd.to_datetime(row.iloc[date_col], errors="coerce")
            else:
                row_date = current_date

            if pd.notna(row_date) and pd.notna(hours_value) and pd.notna(job_value):

                try:
                    hours = float(hours_value)
                except:
                    continue

                full_job_path = str(job_value).strip()

                if full_job_path.lower() in ["nan", "", "none"]:
                    continue

                job_name = full_job_path.split("/")[0].strip()

                rows.append({
                    "Date": row_date,
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


def load_history():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df

    return pd.DataFrame()


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


def show_dashboard(df, title):
    st.subheader(title)

    if df.empty:
        st.info("No data available yet.")
        return

    df = df.copy()

    include_office = st.checkbox(
        f"Include Office hours - {title}",
        value=True
    )

    if not include_office:
        df = df[df["Job"].str.lower() != "office"]

    if df.empty:
        st.warning("No data after filters.")
        return

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

    st.subheader("Hours by Drafter")
    drafter_chart = (
        df.groupby("Drafter")["Hours"]
        .sum()
        .sort_values(ascending=False)
    )
    st.bar_chart(drafter_chart)

    st.subheader("Hours by Job")
    job_chart = (
        df.groupby("Job")["Hours"]
        .sum()
        .sort_values(ascending=False)
    )
    st.bar_chart(job_chart)

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

    st.subheader("Job Breakdown by Drafter")

    job_breakdown = (
        df.groupby(["Job", "Drafter"])["Hours"]
        .sum()
        .reset_index()
        .sort_values(["Job", "Hours"], ascending=[True, False])
    )

    st.dataframe(job_breakdown, use_container_width=True)

    st.subheader("Detailed Hours Log")
    st.dataframe(df, use_container_width=True)


current_df = pd.DataFrame()
history_df = load_history()

if uploaded_file:

    upload_id = get_file_hash(uploaded_file)

    current_df = clean_drafting_hours(uploaded_file)

    if current_df.empty:
        st.error("No usable data found in this Excel file.")

        st.info(
            "This means the report format is still different than expected. "
            "The app could not find the date, hours, and cost center/job columns."
        )

    else:
        st.success("Current file loaded successfully!")

        st.write("Rows found:", len(current_df))

        with st.expander("Preview cleaned data"):
            st.dataframe(current_df, use_container_width=True)

        if st.button("Save Current Upload to Historical Data"):
            history_df = save_to_history(current_df, upload_id)
            st.success("Saved to historical data.")


tab1, tab2 = st.tabs([
    "Current Upload",
    "Current + Historical Data"
])


with tab1:
    show_dashboard(
        current_df,
        "Current Upload"
    )


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
