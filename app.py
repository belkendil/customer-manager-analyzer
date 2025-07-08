import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import warnings

# Try to import fuzzywuzzy, but allow the app to run without it
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    fuzz = None

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Set page config
st.set_page_config(page_title="Customer Manager & Analyzer", layout="wide")

# Function to clean data
def clean_data(df):
    # Remove duplicates based on all columns
    df = df.drop_duplicates()
    # Drop rows with missing values in key columns
    df = df.dropna(subset=['First Name', 'Email'])
    # Drop specified columns
    df = df.drop(columns=['Index', 'Subscription Date'], errors='ignore')
    return df

# Function to extract email domain
def get_email_domain(email):
    try:
        return email.split('@')[1].lower()
    except:
        return 'Unknown'

# Function for company name matching suggestions
def suggest_company_name(input_name, company_list, threshold=80):
    if not FUZZY_AVAILABLE:
        return []
    suggestions = []
    for company in company_list:
        score = fuzz.ratio(input_name.lower(), company.lower())
        if score >= threshold:
            suggestions.append((company, score))
    return sorted(suggestions, key=lambda x: x[1], reverse=True)[:3]

# Load data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('customers-100.csv')
        return clean_data(df)
    except FileNotFoundError:
        st.error("customers-100.csv not found. Please upload the file.")
        return None

# Main app
def main():
    # Load and clean data
    df = load_data()
    if df is None:
        return

    # Sidebar
    st.sidebar.title("Navigation")
    view = st.sidebar.radio("Select View", ["Overview", "Table", "Stats"])

    # Overview View
    if view == "Overview":
        st.header("Customer Data Overview")
        
        # Summary stats
        total_customers = len(df)
        unique_countries = df['Country'].nunique()
        most_common_country = df['Country'].mode()[0] if not df['Country'].empty else "N/A"
        top_cities = df['City'].value_counts().head(3)
        top_companies = df['Company'].value_counts().head(5)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Customers", total_customers)
            st.metric("Number of Countries", unique_countries)
        with col2:
            st.metric("Most Common Country", most_common_country)
        with col3:
            st.subheader("Top 3 Cities")
            st.write(top_cities)
        
        st.subheader("Top 5 Companies")
        st.write(top_companies)

    # Table View
    elif view == "Table":
        st.header("Editable Customer Data")
        
        # Search and filter
        search_term = st.text_input("Search by Name or Company")
        filtered_df = df
        if search_term:
            filtered_df = df[df['First Name'].str.contains(search_term, case=False, na=False) | 
                           df['Company'].str.contains(search_term, case=False, na=False)]
        
        # Company name matching suggestions (only if fuzzywuzzy is available)
        if FUZZY_AVAILABLE:
            st.subheader("Company Name Suggestions")
            company_input = st.text_input("Enter company name for suggestions")
            if company_input:
                company_list = df['Company'].dropna().unique()
                suggestions = suggest_company_name(company_input, company_list)
                if suggestions:
                    st.write("Suggested companies:")
                    for company, score in suggestions:
                        st.write(f"{company} (Match score: {score}%)")
                else:
                    st.write("No close matches found.")
        else:
            st.info("Company name suggestions are disabled. Install 'fuzzywuzzy' to enable this feature.")

        # Editable table
        edited_df = st.data_editor(
            filtered_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Email": st.column_config.TextColumn(
                    "Email",
                    help="Enter a valid email address",
                    validate=r"^[^@]+@[^@]+\.[^@]+$"
                ),
                "Company": st.column_config.TextColumn(
                    "Company",
                    help="Enter company name"
                )
            }
        )
        
        # Export button
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv = edited_df.to_csv(index=False)
        st.download_button(
            label="Download Cleaned Data",
            data=csv,
            file_name=f"cleaned_customers_{timestamp}.csv",
            mime="text/csv"
        )

        # Missing email alert
        if edited_df['Email'].isna().any():
            st.warning("Some records have missing email addresses!")

    # Stats View
    elif view == "Stats":
        st.header("Customer Statistics")

        # Top 5 countries bar chart
        top_countries = df['Country'].value_counts().head(5)
        fig1 = px.bar(x=top_countries.values, y=top_countries.index, 
                     title="Top 5 Countries by Customer Count", 
                     orientation='h',
                     labels={'x': 'Customer Count', 'y': 'Country'})
        st.plotly_chart(fig1, use_container_width=True)

        # Top 5 cities bar chart
        top_cities = df['City'].value_counts().head(5)
        fig2 = px.bar(x=top_cities.values, y=top_cities.index, 
                     title="Top 5 Cities by Customer Count", 
                     orientation='h',
                     labels={'x': 'Customer Count', 'y': 'City'})
        st.plotly_chart(fig2, use_container_width=True)

        # Country distribution pie chart
        country_counts = df['Country'].value_counts()
        top_n = 5
        if len(country_counts) > top_n:
            top_countries = country_counts.head(top_n)
            others_count = country_counts[top_n:].sum()
            top_countries = pd.Series({**top_countries, 'Others': others_count})
        else:
            top_countries = country_counts
        fig3 = px.pie(values=top_countries.values, names=top_countries.index,
                     title=f"Customer Distribution by Country (Top {top_n} + Others)")
        st.plotly_chart(fig3, use_container_width=True)

        # Email domain pie chart
        df['Email Domain'] = df['Email'].apply(get_email_domain)
        email_domains = df['Email Domain'].value_counts()
        fig4 = px.pie(values=email_domains.values, names=email_domains.index,
                     title="Customer Distribution by Email Domain")
        st.plotly_chart(fig4, use_container_width=True)

        # Top 10 companies horizontal bar
        top_companies = df['Company'].value_counts().head(10)
        fig5 = px.bar(x=top_companies.values, y=top_companies.index,
                     title="Top 10 Companies by Customer Count",
                     orientation='h',
                     labels={'x': 'Customer Count', 'y': 'Company'})
        st.plotly_chart(fig5, use_container_width=True)

        # Stacked bar of country and email availability
        df['Has Email'] = ~df['Email'].isna()
        email_by_country = df.groupby(['Country', 'Has Email']).size().unstack(fill_value=0)
        # Ensure both True and False columns exist
        if True not in email_by_country.columns:
            email_by_country[True] = 0
        if False not in email_by_country.columns:
            email_by_country[False] = 0
        fig6 = go.Figure(data=[
            go.Bar(name='Has Email', x=email_by_country.index, y=email_by_country[True]),
            go.Bar(name='Missing Email', x=email_by_country.index, y=email_by_country[False])
        ])
        fig6.update_layout(barmode='stack', title="Customers by Country and Email Availability",
                          xaxis_title="Country", yaxis_title="Customer Count")
        st.plotly_chart(fig6, use_container_width=True)

        # Box plot of company name lengths
        df['Company Name Length'] = df['Company'].str.len()
        fig7 = px.box(df, y='Company Name Length', title="Distribution of Company Name Lengths")
        st.plotly_chart(fig7, use_container_width=True)

if __name__ == "__main__":
    main()