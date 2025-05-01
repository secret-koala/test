import pandas as pd
import requests
from io import BytesIO
from thefuzz import process
import streamlit as st
import numpy as np
import plotly.express as px

# Function to import and clean Excel data from GitHub
@st.cache_data
def import_excel_from_github(sheet_name=0):
    github_raw_url = "https://github.com/maxpquint/econ8320semesterproject/raw/main/UNO%20Service%20Learning%20Data%20Sheet%20De-Identified%20Version.xlsx"
    try:
        response = requests.get(github_raw_url)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content), sheet_name=sheet_name)
        st.write("Excel file successfully loaded into DataFrame.")

        df.replace(to_replace=r'(?i)^missing$', value=np.nan, regex=True, inplace=True)
        df.rename(columns={
            'State': 'Pt State',
            'Payment Submitted': 'Payment Submitted?',
            'Application Signed': 'Application Signed?'
        }, inplace=True)

        if 'Request Status' in df.columns:
            request_status_options = ['pending', 'approved', 'denied', 'completed']
            df['Request Status'] = df['Request Status'].astype(str).apply(
                lambda x: process.extractOne(x.lower().strip(), request_status_options)[0]
                if pd.notna(x) and x.lower().strip() != 'nan' else np.nan)

        if 'Application Signed?' in df.columns:
            application_signed_options = ['yes', 'no', 'n/a']
            df['Application Signed?'] = df['Application Signed?'].astype(str).apply(
                lambda x: process.extractOne(x.lower(), application_signed_options)[0] if pd.notna(x) else 'N/A')

        state_to_postal = {
            "Nebraska": "NE", "Iowa": "IA", "Kansas": "KS", "Missouri": "MO",
            "South Dakota": "SD", "Wyoming": "WY", "Colorado": "CO", "Minnesota": "MN"
        }
        if 'Pt State' in df.columns:
            df['Pt State'] = df['Pt State'].astype(str).apply(
                lambda x: state_to_postal.get(process.extractOne(x, list(state_to_postal.keys()))[0], x)
                if pd.notna(x) and x != 'nan' else x)

        if 'Total Household Gross Monthly Income' in df.columns:
            df['Total Household Gross Monthly Income'] = pd.to_numeric(df['Total Household Gross Monthly Income'], errors='coerce')
            df['Annualized Income'] = df['Total Household Gross Monthly Income'] * 12
            df['Income Level'] = df['Annualized Income'].apply(
                lambda x: "$0–$12,000" if x <= 12000 else
                "$12,001–$47,000" if 12000 < x <= 47000 else
                "$47,001–$100,000" if 47000 < x <= 100000 else
                "$100,000+" if x > 100000 else pd.NA)

        if 'Gender' in df.columns:
            gender_options = ['male', 'female', 'transgender', 'nonbinary', 'decline to answer', 'other']
            df['Gender'] = df['Gender'].astype(str).apply(
                lambda x: process.extractOne(x, gender_options)[0] if pd.notna(x) and x != 'nan' else x)

        if 'Race' in df.columns:
            race_options = [
                'American Indian or Alaska Native', 'Asian', 'Black or African American', 'Middle Eastern or North African',
                'Native Hawaiian or Pacific Islander', 'White', 'decline to answer', 'other', 'two or more']
            df['Race'] = df['Race'].astype(str).apply(
                lambda x: process.extractOne(x, race_options)[0] if pd.notna(x) and x != 'nan' else x)

        if 'Insurance Type' in df.columns:
            insurance_options = [
                'medicare', 'medicaid', 'medicare & medicaid', 'uninsured',
                'private', 'military', 'unknown']
            df['Insurance Type'] = df['Insurance Type'].astype(str).apply(
                lambda x: process.extractOne(x, insurance_options)[0] if pd.notna(x) and x != 'nan' else x)

        if 'Payment Submitted?' in df.columns:
            df['Payment Submitted?'] = pd.to_datetime(df['Payment Submitted?'], errors='coerce')

        if 'Grant Req Date' in df.columns:
            df['Grant Req Date'] = pd.to_datetime(df['Grant Req Date'], errors='coerce')
            df['Year'] = df['Grant Req Date'].dt.year

        if 'Amount' in df.columns:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

        if 'Marital Status' in df.columns:
            marital_options = ['single', 'married', 'widowed', 'divorced', 'domestic partnership', 'separated']
            df['Marital Status'] = df['Marital Status'].astype(str).apply(
                lambda x: process.extractOne(x, marital_options)[0] if pd.notna(x) and x != 'nan' else x)

        if 'Hispanic/Latino' in df.columns:
            df['Hispanic/Latino'] = df['Hispanic/Latino'].apply(
                lambda x: 'No' if 'non' in str(x).lower() else 'Yes' if pd.notna(x) else np.nan)

        if 'Type of Assistance (CLASS)' in df.columns:
            assistance_options = [
                'Medical Supplies/Prescription Co-pay(s)', 'Food/Groceries', 'Gas', 'Other', 'Hotel', 'Housing',
                'Utilities', 'Car Payment', 'Phone/Internet', 'Multiple']
            df['Type of Assistance (CLASS)'] = df['Type of Assistance (CLASS)'].astype(str).apply(
                lambda x: process.extractOne(x.lower(), [i.lower() for i in assistance_options])[0] if pd.notna(x) else x)

        if 'Payment Submitted?' in df.columns and 'Grant Req Date' in df.columns:
            df['Time to Support'] = (df['Payment Submitted?'] - df['Grant Req Date']).dt.days

        return df

    except requests.exceptions.RequestException as e:
        st.write(f"Error: {e}")
        return pd.DataFrame()


# Streamlit App
st.title('UNO Service Learning Data Dashboard')
df = import_excel_from_github()

# Streamlit Sidebar Page Selection
if df is not None:
    page = st.sidebar.selectbox("Select a Page", [
        "Home",
        "Demographic Breakout",
        "Grant Time Difference",
        "Remaining Balance Analysis",
        "Application Signed",
        "Impact & Progress Summary"
    ])

    if page == "Home":
        st.subheader("Welcome to the Home Page!")
        st.write("Updated Column names in the dataset:")
        st.write(df.columns)
        st.write("Data cleaned successfully!")
        st.dataframe(df.head(), use_container_width=True)

        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')

        csv = convert_df(df)
        st.download_button(
            label="Download Cleaned Data",
            data=csv,
            file_name='cleaned_data.csv',
            mime='text/csv'
        )

    elif page == "Demographic Breakout":
        st.subheader("Demographic Breakout Analysis")
        year = st.selectbox("Select Year", df['Year'].unique(), key="year_demo")
        df_year_filtered = df[df['Year'] == year]

        def render_sum(category, label):
            all_values = sorted(df[category].dropna().unique().tolist())
            group = df_year_filtered.groupby(category)['Amount'].sum(min_count=1).reset_index()
            full = pd.DataFrame(all_values, columns=[category]).merge(group, on=category, how='left')
            st.write(f"Total Amount by {label}:")
            st.dataframe(full)

        render_sum('Pt State', 'State')
        render_sum('Gender', 'Gender')
        render_sum('Income Level', 'Income Level')
        render_sum('Insurance Type', 'Insurance Type')
        render_sum('Marital Status', 'Marital Status')
        render_sum('Hispanic/Latino', 'Hispanic/Latino')

    elif page == "Grant Time Difference":
        st.subheader("Time Between Request and Support")

        if 'Grant Req Date' in df.columns and 'Payment Submitted?' in df.columns:
            df['Time to Support'] = (df['Payment Submitted?'] - df['Grant Req Date']).dt.days
            st.write("Distribution of Time to Support (in days):")
            fig = px.histogram(df['Time to Support'].dropna(), nbins=30, title="Time to Support (in days)", 
                                labels={'Time to Support': 'Days'}, opacity=0.75)
            st.plotly_chart(fig)

            st.write("Average Time to Support:", df['Time to Support'].mean())
            st.write("Count:", df['Time to Support'].count())
        else:
            st.write("Required columns are missing in the dataset.")

    elif page == "Remaining Balance Analysis":
        st.subheader("Remaining Balance Analysis")

        if 'Remaining Balance' in df.columns:
            df['Remaining Balance'] = pd.to_numeric(df['Remaining Balance'], errors='coerce')

            if 'Year' in df.columns:
                year = st.selectbox("Select Year", df['Year'].unique(), key="year_balance")
                df_year_filtered = df[df['Year'] == year]
                df_year_filtered_unique = df_year_filtered.drop_duplicates(subset='Patient ID#')

                df_filtered_zero_or_less = df_year_filtered_unique[df_year_filtered_unique['Remaining Balance'] <= 0]
                df_filtered_greater_than_zero = df_year_filtered_unique[df_year_filtered_unique['Remaining Balance'] > 0]

                patient_count_zero_or_less = df_filtered_zero_or_less['Patient ID#'].nunique()
                patient_count_greater_than_zero = df_filtered_greater_than_zero['Patient ID#'].nunique()

                st.write(f"Number of Unique Patients with Remaining Balance <= 0 for Year {year}: {patient_count_zero_or_less}")
                st.write(f"Number of Unique Patients with Remaining Balance > 0 for Year {year}: {patient_count_greater_than_zero}")

                # Pie chart for Remaining Balance <= 0 vs > 0
                fig = px.pie(
                    names=["<= 0", "> 0"], 
                    values=[patient_count_zero_or_less, patient_count_greater_than_zero], 
                    title="Remaining Balance: Unique Patient Distribution"
                )
                st.plotly_chart(fig)

                st.write("Unique Patients with Remaining Balance <= 0:")
                st.dataframe(df_filtered_zero_or_less[['Patient ID#', 'Remaining Balance']])

                st.write("Unique Patients with Remaining Balance > 0:")
                st.dataframe(df_filtered_greater_than_zero[['Patient ID#', 'Remaining Balance']])

                # Total amount by Type of Assistance
                if 'Type of Assistance (CLASS)' in df.columns:
                    st.write("Total Amount by Type of Assistance (CLASS):")
                    assistance_sum = df_year_filtered.groupby('Type of Assistance (CLASS)')['Amount'].sum(min_count=1).reset_index()

                    # Pie chart for Type of Assistance
                    fig = px.pie(
                        assistance_sum, 
                        names='Type of Assistance (CLASS)', 
                        values='Amount', 
                        title="Total Amount by Type of Assistance"
                    )
                    st.plotly_chart(fig)
            else:
                st.write("The 'Year' column is missing in the dataset.")
        else:
            st.write("The 'Remaining Balance' column is missing in the dataset.")

    elif page == "Application Signed":
        st.subheader("Application Signed Data")

        if 'Request Status' in df.columns:
            df_pending = df[df['Request Status'] == 'pending']
            st.write(f"Displaying records where 'Request Status' is 'pending':")
            st.dataframe(df_pending[['Patient ID#', 'Application Signed?', 'Request Status', 'Year']])
        else:
            st.write("The 'Request Status' column is missing in the dataset.")

    elif page == "Impact & Progress Summary":
        st.subheader("Impact & Progress Summary")
        required_cols = ['Amount', 'Patient ID#', 'Time to Support', 'Application Signed?', 'Remaining Balance', 'Pt State']
        if all(col in df.columns for col in required_cols):
            year = st.selectbox("Select Year", df['Year'].unique(), key="year_impact")
            df_year_filtered = df[df['Year'] == year]
            
            total_amount = df_year_filtered['Amount'].sum()
            patients_served = df_year_filtered['Patient ID#'].nunique()
            avg_support_time = df_year_filtered['Time to Support'].mean()
            signed_apps = df_year_filtered['Application Signed?'].str.lower().eq('yes').sum()
            signed_pct = (signed_apps / len(df_year_filtered)) * 100 if len(df_year_filtered) > 0 else 0
            fully_utilized_pct = (df_year_filtered[df_year_filtered['Remaining Balance'] <= 0]['Patient ID#'].nunique() / patients_served) * 100 if patients_served > 0 else 0

            st.markdown("### Key Highlights")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Grants Disbursed", f"${total_amount:,.0f}")
            col2.metric("Patients Served", patients_served)
            col3.metric("Avg. Time to Support", f"{avg_support_time:.1f} days" if not np.isnan(avg_support_time) else "N/A")

            col4, col5 = st.columns(2)
            col4.metric("Application Completion", f"{signed_pct:.1f}%")
            col5.metric("Fully Utilized Grants", f"{fully_utilized_pct:.1f}%")

            st.divider()

            # Total Grants Over Time
            if 'Year' in df.columns:
                amount_trend = df.groupby('Year')['Amount'].sum().reset_index()  # Group by year
                fig_trend = px.bar(amount_trend, x='Year', y='Amount', title="Total Grants Over Time")
                st.plotly_chart(fig_trend)

            # Grants by State for Selected Year
            state_grant_count = df_year_filtered.groupby('Pt State')['Amount'].sum().reset_index()
            fig_map = px.choropleth(
                state_grant_count,
                locations='Pt State',
                locationmode="USA-states",
                color='Amount',
                hover_name='Pt State',
                color_continuous_scale="Viridis",
                title="Grants by State"
            )
            st.plotly_chart(fig_map)

        else:
            st.write("Data is missing some required columns for impact summary.")

















