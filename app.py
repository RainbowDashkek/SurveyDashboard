import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Page Configuration (This builds the UI layout)
st.set_page_config(page_title="Project Survey Dashboard", layout="wide")
st.title("Project Survey Dashboard")

# 2. Retrieve the secret URL securely from Streamlit's secrets
try:
    sosci_url = st.secrets["SOSCI_API_URL"]
except (KeyError, FileNotFoundError):
    sosci_url = None

if sosci_url:
    # ON THE CLOUD: Pull live data from SoSci Survey
    # We cache this function for 5 minutes (300 seconds) so the app loads instantly
    # and doesn't spam SoSci Survey's server on every page refresh.
    @st.cache_data(ttl=300)
    def load_data(url):
        return pd.read_csv(url)
    
    df = load_data(sosci_url)
else:
    # LOCAL FALLBACK: If running on your computer, use dummy data
    np.random.seed(42)
    df = pd.DataFrame({
        'age': np.random.randint(18, 70, size=150),
        'income': pd.Categorical(
            np.random.choice(["<500", "500-1500", ">1500"], size=150),
            categories=["<500", "500-1500", ">1500"],
            ordered=True
        ),
        'gender': np.random.choice(["Female", "Male", "Non-binary"], size=150)
    })

# 3. Create a KPI Metric Card at the top
st.metric(label="Total Respondents", value=len(df))

# 4. Create two columns for the charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Income Distribution")
    fig1 = px.histogram(
        df, 
        x="income", 
        color="income",
        color_discrete_sequence=px.colors.sequential.Blues_r,
        category_orders={"income": ["<500", "500-1500", ">1500"]}
    )
    fig1.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Count", template="simple_white")
    # Streamlit places the plotly chart cleanly into the left column
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Age Distribution")
    fig2 = px.histogram(
        df, 
        x="age",
        nbins=10,
        color_discrete_sequence=["#4682B4"]
    )
    fig2.update_layout(xaxis_title="Age (Years)", yaxis_title="Count", template="simple_white")
    # Streamlit places the plotly chart cleanly into the right column
    st.plotly_chart(fig2, use_container_width=True)
