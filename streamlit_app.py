import pandas as pd
import numpy as np
import requests
from thefuzz import process
import streamlit as st
import plotly.express as px

# ─── Helper functions ─────────────────────────────────────────────────────────

def fuzzy_map(series: pd.Series, options: list[str], default=np.nan, lower: bool = True) -> pd.Series:
    """
    Fuzzy-match each value in `series` to the closest member of `options`.
    Returns the matched option or `default` if input is null or can't match.
    """
    opts = [opt.lower() if lower else opt for opt in options]
    def _match(val):
        if pd.isna(val):
            return default
        text = val.lower() if lower else str(val)
        match, score = process.extractOne(text, opts)
        return match if score >= 60 else default
    return series.astype(str).apply(_match)

@st.cache_data
def import_and_clean(sheet_name: int = 0) -> pd.DataFrame:
    # 1) Load
    url = ("https://github.com/StefVarg1/Semester-Project/raw/refs/heads/main/UNO%20Service%20Learning%20Data%20Sheet%20De-Identified%20Version.xlsx")
    df = pd.read_excel((url), sheet_name=sheet_name)
    st.write("✅ Excel file successfully loaded.")

    # 2) Base clean
    df.replace(to_replace=r'(?i)^missing$', value=np.nan, regex=True, inplace=True)
    df.rename(columns={
        'State': 'Pt State',
        'Payment Submitted': 'Payment Submitted?',
        'Application Signed': 'Application Signed?'
    }, inplace=True)

    # 3) Fuzzy-standardize categories
    if 'Request Status' in df:
        df['Request Status'] = fuzzy_map(
            df['Request Status'],
            ['pending', 'approved', 'denied', 'completed']
        )

    if 'Application Signed?' in df:
        df['Application Signed?'] = fuzzy_map(
            df['Application Signed?'],
            ['yes', 'no', 'n/a'],
            default='N/A'
        )

    if 'Gender' in df:
        df['Gender'] = fuzzy_map(
            df['Gender'],
            ['male', 'female', 'transgender', 'nonbinary', 'decline to answer', 'other']
        )

    if 'Race' in df:
        df['Race'] = fuzzy_map(
            df['Race'],
            [
                'American Indian or Alaska Native', 'Asian',
                'Black or African American', 'Middle Eastern or North African',
                'Native Hawaiian or Pacific Islander', 'White',
                'decline to answer', 'other', 'two or more'
            ],
            lower=False
        )

    if 'Insurance Type' in df:
        df['Insurance Type'] = fuzzy_map(
            df['Insurance Type'],
            ['medicare', 'medicaid', 'medicare & medicaid',
             'uninsured', 'private', 'military', 'unknown']
        )

    if 'Marital Status' in df:
        df['Marital Status'] = fuzzy_map(
            df['Marital Status'],
            ['single', 'married', 'widowed', 'divorced',
             'domestic partnership', 'separated']
        )

    if 'Type of Assistance (CLASS)' in df:
        assistance_opts = [
            'Medical Supplies/Prescription Co-pay(s)', 'Food/Groceries', 'Gas',
            'Other', 'Hotel', 'Housing', 'Utilities', 'Car Payment',
            'Phone/Internet', 'Multiple'
        ]
        df['Type of Assistance (CLASS)'] = fuzzy_map(
            df['Type of Assistance (CLASS)'],
            assistance_opts,
            lower=False
        )

    # 4) State → Postal
    state_to_postal = {
        "Nebraska": "NE", "Iowa": "IA", "Kansas": "KS", "Missouri": "MO",
        "South Dakota": "SD", "Wyoming": "WY", "Colorado": "CO", "Minnesota": "MN"
    }
    if 'Pt State' in df:
        def map_state(x):
            if pd.isna(x) or x.lower().strip() == 'nan':
                return x
            match = process.extractOne(x, list(state_to_postal))
            return state_to_postal.get(match[0], x) if match else x
        df['Pt State'] = df['Pt State'].astype(str).apply(map_state)

    # 5) Dates & year
    if 'Payment Submitted?' in df:
        df['Payment Submitted?'] = pd.to_datetime(df['Payment Submitted?'], errors='coerce')
    if 'Grant Req Date' in df:
        df['Grant Req Date'] = pd.to_datetime(df['Grant Req Date'], errors='coerce')
        df['Year'] = df['Grant Req Date'].dt.year

    # 6) Numeric transforms
    if 'Total Household Gross Monthly Income' in df:
        df['Total Household Gross Monthly Income'] = pd.to_numeric(
            df['Total Household Gross Monthly Income'], errors='coerce'
        )
        df['Annualized Income'] = df['Total Household Gross Monthly Income'] * 12
        def income_bracket(x):
            if pd.isna(x):
                return pd.NA
            if x <= 12_000:
                return "$0–$12,000"
            if x <= 47_000:
                return "$12,001–$47,000"
            if x <= 100_000:
                return "$47,001–$100,000"
            return "$100,000+"
        df['Income Level'] = df['Annualized Income'].apply(income_bracket)

    if 'Amount' in df:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    if 'Remaining Balance' in df:
        df['Remaining Balance'] = pd.to_numeric(df['Remaining Balance'], errors='coerce')

    # 7) Hispanic/Latino flag
    if 'Hispanic/Latino' in df:
        df['Hispanic/Latino'] = df['Hispanic/Latino'].apply(
            lambda x: 'No' if pd.notna(x) and 'non' in str(x).lower()
                      else 'Yes' if pd.notna(x)
                      else np.nan
        )

    return df


# ─── Streamlit App ────────────────────────────────────────────────────────────

st.set_page_config(page_title="UNO Service Learning Data Dashboard")
st.title("UNO Service Learning Data Dashboard")

df = import_and_clean()

if df.empty:
    st.error("Failed to load data.")
    st.stop()

# Precompute CSV for download
@st.cache_data
def to_csv(data: pd.DataFrame) -> bytes:
    return data.to_csv(index=False).encode('utf-8')

# Sidebar navigation
page = st.sidebar.selectbox(
    "Go to",
    ["Home", "Demographic Breakout", "Grant Time Difference",
     "Remaining Balance Analysis", "Application Signed"]
)

if page == "Home":
    st.subheader("Home")
    st.write("**Columns:**", list(df.columns))
    st.dataframe(df.head(), use_container_width=True)
    st.download_button(
        "Download Cleaned Data",
        data=to_csv(df),
        file_name="cleaned_data.csv",
        mime="text/csv"
    )

elif page == "Demographic Breakout":
    st.subheader("Demographic Breakout")
    year = st.selectbox("Year", sorted(df['Year'].dropna().unique()), key="demo_year")
    df_y = df[df['Year'] == year]

    def show_breakout(col, title):
        st.write(f"**Total Amount by {title}:**")
        grp = df_y.groupby(col)['Amount'].sum(min_count=1).reset_index()
        all_opts = pd.DataFrame({col: sorted(df[col].dropna().unique())})
        st.dataframe(all_opts.merge(grp, on=col, how='left'), use_container_width=True)

    for col, title in [
        ("Pt State", "State"), ("Gender", "Gender"),
        ("Income Level", "Income Level"),
        ("Insurance Type", "Insurance Type"),
        ("Marital Status", "Marital Status"),
        ("Hispanic/Latino", "Hispanic/Latino")
    ]:
        if col in df_y:
            show_breakout(col, title)

elif page == "Grant Time Difference":
    st.subheader("Time Between Request and Support")
    year = st.selectbox("Year", sorted(df['Year'].dropna().unique()), key="time_year")
    df_y = df[df['Year'] == year]
    if {'Grant Req Date', 'Payment Submitted?'}.issubset(df_y.columns):
        df_y['Time to Support'] = (
            df_y['Payment Submitted?'] - df_y['Grant Req Date']
        ).dt.days
        st.write("Distribution of Time to Support (days):")
        fig = px.histogram(
            df_y['Time to Support'].dropna(),
            nbins=30,
            labels={'value': 'Days', 'count': 'Requests'}
        )
        st.plotly_chart(fig)
        st.write("Average:", round(df_y['Time to Support'].mean(), 1))
        st.write("Count:", df_y['Time to Support'].count())
    else:
        st.warning("Missing date columns for this analysis.")

elif page == "Remaining Balance Analysis":
    st.subheader("Remaining Balance Analysis")
    year = st.selectbox("Year", sorted(df['Year'].dropna().unique()), key="bal_year")
    df_y = df[df['Year'] == year]
    if 'Remaining Balance' in df_y:
        unique = df_y.drop_duplicates(subset='Patient ID#')
        low = unique[unique['Remaining Balance'] <= 0]
        high = unique[unique['Remaining Balance'] > 0]
        st.write(f"≤ 0: {low['Patient ID#'].nunique()} patients")
        st.write(f"> 0: {high['Patient ID#'].nunique()} patients")
        fig = px.pie(
            names=["Used all balance", "Did not use all"],
            values=[low['Patient ID#'].nunique(), high['Patient ID#'].nunique()]
        )
        st.plotly_chart(fig)
        st.dataframe(low[['Patient ID#', 'Remaining Balance']], use_container_width=True)
        st.dataframe(high[['Patient ID#', 'Remaining Balance']], use_container_width=True)
        if 'Type of Assistance (CLASS)' in df_y:
            st.subheader("By Assistance Type")
            assist_sum = df_y.groupby('Type of Assistance (CLASS)')['Amount'].sum(min_count=1).reset_index()
            fig2 = px.pie(
                assist_sum,
                names='Type of Assistance (CLASS)',
                values='Amount'
            )
            st.plotly_chart(fig2)
    else:
        st.warning("No Remaining Balance data for this year.")

elif page == "Application Signed":
    st.subheader("Applications Pending Signature")
    year = st.selectbox("Year", sorted(df['Year'].dropna().unique()), key="sign_year")
    df_y = df[df['Year'] == year]
    if {'Request Status', 'Application Signed?'}.issubset(df_y.columns):
        pending = df_y[df_y['Request Status'] == 'pending']
        st.dataframe(
            pending[['Patient ID#', 'Application Signed?', 'Request Status', 'Year']],
            use_container_width=True
        )
    else:
        st.warning("Required columns missing.")