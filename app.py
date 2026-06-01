import os
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Page Configuration
st.set_page_config(page_title="Survey Project Dashboard", layout="wide")
st.title("Project Survey Dashboard")

# 2. Retrieve the secret URL securely from Streamlit's secrets
try:
    sosci_url = st.secrets["SOSCI_API_URL"]
except (KeyError, FileNotFoundError):
    sosci_url = None

# Halt the app if the secret is not configured
if not sosci_url:
    st.warning("Please configure your `SOSCI_API_URL` secret to run the dashboard.")
    st.stop()

# --- CODEBOOK DICTIONARIES ---
income_map = {
    2: "< 500€",
    3: "500 - 1500€",
    5: "1500 - 2500€",
    8: "2500 - 3500€",
    10: "3500 - 4500€",
    13: "4500 - 5500€",
    14: "5500 - 6500€",
    15: "6500 - 7500€",
    16: "7500 - 8500€",
    11: "> 8500€"
}
income_categories = [
    "< 500€", "500 - 1500€", "1500 - 2500€", "2500 - 3500€", 
    "3500 - 4500€", "4500 - 5500€", "5500 - 6500€", "6500 - 7500€", 
    "7500 - 8500€", "> 8500€"
]

age_map = {
    1: "< 15",
    2: "15 - 19",
    3: "20 - 24",
    4: "25 - 29",
    5: "30 - 34",
    6: "35 - 39",
    7: "40 - 44",
    8: "45 - 49",
    9: "50 - 54",
    10: "55 - 59",
    11: "60 - 64",
    12: "65 - 74",
    13: "> 74"
}
age_categories = [
    "< 15", "15 - 19", "20 - 24", "25 - 29", "30 - 34", 
    "35 - 39", "40 - 44", "45 - 49", "50 - 54", "55 - 59", 
    "60 - 64", "65 - 74", "> 74"
]

gender_map = {
    1: "weiblich",
    2: "männlich",
    3: "divers"
}
gender_categories = ["weiblich", "männlich", "divers"]

country_map = {
    1: "Deutschland",
    2: "Österreich",
    3: "Schweiz",
    4: "Anderes Land"
}

profession_map = {
    1: "Forschung & Entwicklung",
    2: "IT / Technik / Ingenieur",
    3: "Medizin / Gesundheit / Pflege",
    4: "Bildung / Erziehung",
    5: "Geistes- & Sozialwiss.",
    6: "Öffentl. Dienst / NGO",
    7: "Recht / Finanzen",
    8: "Marketing / Medien",
    9: "Handwerk / Produktion",
    10: "Landwirtsch. / Umwelt",
    11: "Gastro / Tourismus",
    12: "Kunst / Kultur",
    13: "Nicht erwerbstätig (Schüler/Rente)",
    14: "Sonstiges"
}


# ON THE CLOUD & LOCAL: Pull live data from SoSci Survey
@st.cache_data(ttl=300)
def load_data(url):
    return pd.read_csv(url, encoding="utf-16", sep="\t")

raw_df = load_data(sosci_url)

# -------------------------------------------------------------
# 1. SURVEY PROGRESS ANALYSIS (Using All Cases)
# -------------------------------------------------------------
total_started = len(raw_df)

# Completed cases (Reached Page 9)
df_finished_raw = raw_df[raw_df['LASTPAGE'] >= 9].copy()
total_finished = len(df_finished_raw)

# Unfinished cases (Dropouts before Page 9)
df_unfinished = raw_df[raw_df['LASTPAGE'] < 9].copy()

# Group dropouts by page
dropout_data = df_unfinished['LASTPAGE'].value_counts().reset_index()
dropout_data.columns = ['Page', 'Dropouts']
dropout_data = dropout_data.sort_values(by='Page')

# Response Timeline Calculations (Cumulative)
raw_df['STARTED'] = pd.to_datetime(raw_df['STARTED'], errors='coerce')
df_finished_raw['STARTED'] = pd.to_datetime(df_finished_raw['STARTED'], errors='coerce')

daily_starts = raw_df.groupby(raw_df['STARTED'].dt.date).size().reset_index()
daily_starts.columns = ['Date', 'Gestartet']

daily_completes = df_finished_raw.groupby(df_finished_raw['STARTED'].dt.date).size().reset_index()
daily_completes.columns = ['Date', 'Ausgefüllt']

timeline_data = pd.merge(daily_starts, daily_completes, on='Date', how='outer').fillna(0)
timeline_data = timeline_data.sort_values(by='Date')
timeline_data['Gestartet_Cum'] = timeline_data['Gestartet'].cumsum()
timeline_data['Ausgefüllt_Cum'] = timeline_data['Ausgefüllt'].cumsum()

timeline_melted = timeline_data.melt(
    id_vars='Date', 
    value_vars=['Gestartet_Cum', 'Ausgefüllt_Cum'], 
    var_name='Status', 
    value_name='Count'
)
timeline_melted['Status'] = timeline_melted['Status'].map({
    'Gestartet_Cum': 'Gestartet (insgesamt)',
    'Ausgefüllt_Cum': 'Ausgefüllt (insgesamt)'
})

# -------------------------------------------------------------
# 2. DATA PROCESSING & CLEANING (Completed Cases Only)
# -------------------------------------------------------------
df = pd.DataFrame()

# Demographics
df['income'] = df_finished_raw['SD16'].map(income_map)
df['income'] = pd.Categorical(df['income'], categories=income_categories, ordered=True)

df['age'] = df_finished_raw['SD03'].map(age_map)
df['age'] = pd.Categorical(df['age'], categories=age_categories, ordered=True)

df['gender'] = df_finished_raw['SD05'].map(gender_map)
df['gender'] = pd.Categorical(df['gender'], categories=gender_categories, ordered=True)

df['country'] = df_finished_raw['SD07'].map(country_map)
df['profession'] = df_finished_raw['SD19'].map(profession_map)

# Reading Behavior
df['read_luchs'] = df_finished_raw['PF04_01'] == 2
df['read_bart'] = df_finished_raw['PF04_02'] == 2
df['read_apollo'] = df_finished_raw['PF04_03'] == 2
df['read_salam'] = df_finished_raw['PF04_04'] == 2
df['read_count'] = df['read_luchs'].astype(int) + df['read_bart'].astype(int) + df['read_apollo'].astype(int) + df['read_salam'].astype(int)

def categorize_reading(count):
    if count == 4:
        return "Alle (4)"
    elif count == 0:
        return "Keine (0)"
    else:
        return f"Teilweise ({count})"
df['read_all_status'] = df['read_count'].apply(categorize_reading)

# Donations
df['general_donate'] = df_finished_raw['AF03'].map({1: "Nein", 2: "Ja", 3: "Keine Angabe"})

for col in ['P103_02', 'P203_02', 'P303_02', 'P403_02']:
    df_finished_raw[col] = pd.to_numeric(df_finished_raw[col], errors='coerce').fillna(0)

df['donation_amount'] = (
    df_finished_raw['P103_02'] + 
    df_finished_raw['P203_02'] + 
    df_finished_raw['P303_02'] + 
    df_finished_raw['P403_02']
)
df['donated_at_all'] = df['donation_amount'].apply(lambda x: "Ja" if x > 0 else "Nein")


# =============================================================================
# 3. SIDEBAR FILTER SECTIONS (Left panel)
# =============================================================================
st.sidebar.header("Filter-Optionen")
st.sidebar.markdown("Diese Filter gelten für die Bereiche **Demografie**, **Leseverhalten** und **Spendenverhalten**.")

# Filter dropdowns
f_age = st.sidebar.selectbox("Alter:", ["Alle"] + age_categories)
f_gender = st.sidebar.selectbox("Geschlecht:", ["Alle"] + gender_categories)
f_prev_donate = st.sidebar.selectbox("Schon einmal gespendet?", ["Alle", "Ja", "Nein", "Keine Angabe"])

# Safely extract unique professions to avoid crashes
unique_professions = sorted(list(df['profession'].dropna().unique())) if 'profession' in df else []
f_prof = st.sidebar.selectbox("Tätigkeitsfeld / Branche:", ["Alle"] + unique_professions)

# Apply filters to a separate filtered dataframe
df_filtered = df.copy()

if f_age != "Alle":
    df_filtered = df_filtered[df_filtered['age'] == f_age]

if f_gender != "Alle":
    df_filtered = df_filtered[df_filtered['gender'] == f_gender]

if f_prof != "Alle":
    df_filtered = df_filtered[df_filtered['profession'] == f_prof]

if f_prev_donate != "Alle":
    df_filtered = df_filtered[df_filtered['general_donate'] == f_prev_donate]


# =============================================================================
# VISUAL LAYOUT (WITH TABS)
# =============================================================================

# Create Dashboard Tabs
tab_progress, tab_demo, tab_reading, tab_donation, tab_rankings = st.tabs([
    "📈 Survey-Verlauf", 
    "👥 Demografie", 
    "📖 Leseverhalten", 
    "💶 Spendenverhalten",
    "🏆 Rankings & Vergleiche"
])

# -----------------------------------------------------------------------------
# TAB 1: SURVEY PROGRESS & TIMELINE (Always uses UNFILTERED data)
# -----------------------------------------------------------------------------
with tab_progress:
    st.header("Survey-Verlauf & Abbruchstatistik")
    st.info("Hinweis: Diese Verlaufsgrafiken basieren immer auf allen gestarteten Interviews, da für abgebrochene Interviews naturgemäß keine demografischen Daten vorliegen.")
    
    # KPI metrics
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric(label="Begonnene Interviews (Total)", value=total_started)
    m_col2.metric(label="Abgeschlossene Interviews (Seite 9+)", value=total_finished)

    if total_started > 0:
        completion_rate = round((total_finished / total_started) * 100, 1)
    else:
        completion_rate = 0.0
    m_col3.metric(label="Abschlussquote (Completion Rate)", value=f"{completion_rate}%")

    st.markdown("---")

    # Response Timeline
    st.subheader("Rücklauf im Zeitverlauf (Akkumuliert)")
    if len(timeline_melted) > 0:
        fig_timeline = px.line(
            timeline_melted,
            x="Date",
            y="Count",
            color="Status",
            markers=True,
            color_discrete_map={
                "Gestartet (insgesamt)": "#2ecc71", 
                "Ausgefüllt (insgesamt)": "#3498db"
            }
        )
        fig_timeline.update_layout(xaxis_title=None, yaxis_title="Anzahl", template="simple_white", legend_title=None)
        st.plotly_chart(fig_timeline, width='stretch')

    st.markdown("---")

    # Dropout Chart
    st.subheader("Abbrüche nach Fragebogenseite")
    if len(dropout_data) > 0:
        fig_funnel = px.bar(
            dropout_data,
            x="Page",
            y="Dropouts",
            color_discrete_sequence=["#e74c3c"]
        )
        fig_funnel.update_layout(
            xaxis_title="Letzte erfolgreich ausgefüllte Seite",
            yaxis_title="Anzahl Abbrüche",
            template="simple_white",
            xaxis=dict(tickmode='linear', tick0=1, dtick=1)
        )
        st.plotly_chart(fig_funnel, width='stretch')
    else:
        st.info("Bisher keine Abbrüche verzeichnet.")


# -----------------------------------------------------------------------------
# TAB 2: DEMOGRAPHICS (Uses FILTERED data)
# -----------------------------------------------------------------------------
with tab_demo:
    st.header("Teilnehmer-Demografie")
    
    # Check if filters left us with zero rows
    if len(df_filtered) == 0:
        st.warning("Keine Daten für diese Filterkombination vorhanden. Bitte passe deine Filter in der linken Seitenleiste an.")
    else:
        st.caption(f"Zeige gefilterte Daten für N = {len(df_filtered)} von {total_finished} abgeschlossenen Interviews")
        
        col_gender, col_country = st.columns(2)
        
        with col_gender:
            st.subheader("Geschlechterverteilung")
            gender_clean = df_filtered.dropna(subset=['gender'])
            
            gender_colors = {
                "weiblich": "#F9B7B2",
                "männlich": "#B2D8F9",
                "divers": "#B2F9D8"
            }
            
            fig_gender = px.pie(
                gender_clean, 
                names="gender", 
                color="gender",
                color_discrete_map=gender_colors
            )
            fig_gender.update_traces(textinfo='percent+label')
            fig_gender.update_layout(template="simple_white", showlegend=True)
            st.plotly_chart(fig_gender, width='stretch')

        with col_country:
            st.subheader("Herkunft (Land)")
            country_clean = df_filtered.dropna(subset=['country'])
            fig_country = px.histogram(country_clean, x="country", color="country", color_discrete_sequence=px.colors.qualitative.Set2)
            fig_country.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Anzahl", template="simple_white")
            st.plotly_chart(fig_country, width='stretch')

        st.markdown("---")

        col_income, col_age = st.columns(2)

        with col_income:
            st.subheader("Haushaltseinkommen")
            income_clean = df_filtered.dropna(subset=['income'])
            fig1 = px.histogram(
                income_clean, 
                x="income", 
                color="income",
                color_discrete_sequence=px.colors.sequential.Blues_r,
                category_orders={"income": income_categories}
            )
            fig1.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Anzahl", template="simple_white")
            st.plotly_chart(fig1, width='stretch')

        with col_age:
            st.subheader("Altersverteilung")
            age_clean = df_filtered.dropna(subset=['age'])
            fig2 = px.histogram(
                age_clean, 
                x="age",
                color="age",
                color_discrete_sequence=px.colors.sequential.Tealgrn_r,
                category_orders={"age": age_categories}
            )
            fig2.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Anzahl", template="simple_white")
            st.plotly_chart(fig2, width='stretch')

        st.markdown("---")
        
        st.subheader("Tätigkeitsfeld / Berufsbranche")
        profession_clean = df_filtered.dropna(subset=['profession'])
        fig_prof = px.histogram(
            profession_clean,
            y="profession",
            color="profession",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_prof.update_layout(showlegend=False, yaxis_title=None, xaxis_title="Anzahl", template="simple_white")
        st.plotly_chart(fig_prof, width='stretch')


# -----------------------------------------------------------------------------
# TAB 3: READING BEHAVIOR (Uses FILTERED data)
# -----------------------------------------------------------------------------
with tab_reading:
    st.header("Lese- und Informationsverhalten")
    
    if len(df_filtered) == 0:
        st.warning("Keine Daten für diese Filterkombination vorhanden. Bitte passe deine Filter in der linken Seitenleiste an.")
    else:
        st.caption(f"Zeige gefilterte Daten für N = {len(df_filtered)} von {total_finished} abgeschlossenen Interviews")
        
        col_read_all, col_which_read = st.columns(2)
        
        with col_read_all:
            st.subheader("Wurden alle Beschreibungen gelesen?")
            fig_read_all = px.pie(
                df_filtered, 
                names="read_all_status", 
                color_discrete_sequence=px.colors.qualitative.Safe,
                category_orders={"read_all_status": ["Alle (4)", "Teilweise (3)", "Teilweise (2)", "Teilweise (1)", "Keine (0)"]}
            )
            fig_read_all.update_traces(textinfo='percent+label')
            fig_read_all.update_layout(template="simple_white")
            st.plotly_chart(fig_read_all, width='stretch')
            
        with col_which_read:
            st.subheader("Welche Beschreibungen wurden gelesen?")
            animal_counts = pd.DataFrame({
                "Tierart": ["Luchs", "Bartgeier", "Apollofalter", "Alpensalamander"],
                "Anzahl Gelesen": [df_filtered['read_luchs'].sum(), df_filtered['read_bart'].sum(), df_filtered['read_apollo'].sum(), df_filtered['read_salam'].sum()]
            })
            fig_animals = px.bar(
                animal_counts,
                x="Tierart",
                y="Anzahl Gelesen",
                color="Tierart",
                color_discrete_sequence=px.colors.qualitative.Vivid
            )
            fig_animals.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Gelesene Texte", template="simple_white")
            st.plotly_chart(fig_animals, width='stretch')


# -----------------------------------------------------------------------------
# TAB 4: DONATION BEHAVIOR (Uses FILTERED data)
# -----------------------------------------------------------------------------
with tab_donation:
    st.header("Spendenverhalten")
    
    if len(df_filtered) == 0:
        st.warning("Keine Daten für diese Filterkombination vorhanden. Bitte passe deine Filter in der linken Seitenleiste an.")
    else:
        st.caption(f"Zeige gefilterte Daten für N = {len(df_filtered)} von {total_finished} abgeschlossenen Interviews")
        
        # KPI Spendenhöhe metrics (using the filtered dataframe)
        m_col_don_rate, m_col_avg_all, m_col_avg_donors = st.columns(3)
        
        # 1. Study Donation Rate (Filtered)
        total_finished_tab = len(df_filtered)
        donors_count = (df_filtered['donated_at_all'] == "Ja").sum()
        donation_rate = round((donors_count / total_finished_tab) * 100, 1) if total_finished_tab > 0 else 0
        m_col_don_rate.metric(label="Spendenbereitschaft in dieser Studie", value=f"{donation_rate}%")
        
        # 2. Average Donation across everyone in the filtered subgroup
        avg_all = round(df_filtered['donation_amount'].mean(), 2) if total_finished_tab > 0 else 0
        m_col_avg_all.metric(label="Ø Spendenhöhe (Über alle in dieser Gruppe)", value=f"{avg_all} €")
        
        # 3. Average Donation only among active donors in the filtered subgroup
        active_donors = df_filtered[df_filtered['donation_amount'] > 0]
        avg_donors = round(active_donors['donation_amount'].mean(), 2) if len(active_donors) > 0 else 0
        m_col_avg_donors.metric(label="Ø Spendenhöhe (Nur Spender)", value=f"{avg_donors} €")
        
        st.markdown("---")
        
        col_gen_don, col_study_don = st.columns(2)
        
        with col_gen_don:
            st.subheader("Generelle Spendenbereitschaft für Artenschutz (AF03)")
            gen_don_clean = df_filtered.dropna(subset=['general_donate'])
            
            gen_don_colors = {
                "Ja": "#2ecc71",
                "Nein": "#e74c3c",
                "Keine Angabe": "#95a5a6"
            }
            
            fig_gen_don = px.pie(
                gen_don_clean, 
                names="general_donate", 
                color="general_donate",
                color_discrete_map=gen_don_colors
            )
            fig_gen_don.update_traces(textinfo='percent+label')
            fig_gen_don.update_layout(template="simple_white")
            st.plotly_chart(fig_gen_don, width='stretch')
            
        with col_study_don:
            st.subheader("Tatsächliche Spende in der Studie getätigt?")
            
            study_don_colors = {
                "Ja": "#2ecc71",
                "Nein": "#e74c3c"
            }
            
            fig_study_don = px.pie(
                df_filtered, 
                names="donated_at_all", 
                color="donated_at_all",
                color_discrete_map=study_don_colors,
                category_orders={"donated_at_all": ["Nein", "Ja"]}
            )
            fig_study_don.update_traces(textinfo='percent+label')
            fig_study_don.update_layout(template="simple_white")
            st.plotly_chart(fig_study_don, width='stretch')


# -----------------------------------------------------------------------------
# TAB 5: RANKINGS & COMPARISONS (Uses UNFILTERED completed data for reliable sample sizes)
# -----------------------------------------------------------------------------
with tab_rankings:
    st.header("🏆 Rankings & Vergleiche")
    st.markdown("""
    Finde heraus, welche demografischen Gruppen die höchste Spendenbereitschaft zeigen.
    *Diese Rankings basieren auf allen vollständig ausgefüllten Fragebögen, um statistisch verlässliche Gruppengrößen abzubilden.*
    """)
    st.markdown("---")
    
    col_rank1, col_rank2 = st.columns(2)
    with col_rank1:
        rank_var = st.selectbox(
            "Vergleiche Gruppen nach:",
            options=["Tätigkeitsfeld", "Alter", "Geschlecht", "Herkunft (Land)"]
        )
    with col_rank2:
        rank_metric = st.selectbox(
            "Ranking-Maßstab:",
            options=["Durchschnittliche Spendenhöhe (€)", "Spendenquote (%)"]
        )
        
    # Map selection to the actual dataframe column names
    column_mapping = {
        "Tätigkeitsfeld": "profession",
        "Alter": "age",
        "Geschlecht": "gender",
        "Herkunft (Land)": "country"
    }
    col_to_rank = column_mapping[rank_var]
    
    # Filter out empty answers for clean grouping
    df_clean = df.dropna(subset=[col_to_rank])
    
    if len(df_clean) > 0:
        # 1. Calculate sample sizes (N) per category
        counts_df = df_clean[col_to_rank].value_counts().reset_index()
        counts_df.columns = [col_to_rank, 'N']
        
        # 2. Calculate the metrics safely without pandas warning issues
        if rank_metric == "Durchschnittliche Spendenhöhe (€)":
            metric_df = df_clean.groupby(col_to_rank, observed=False)['donation_amount'].mean().reset_index()
            metric_df.columns = [col_to_rank, 'Wert']
            x_title = "Durchschnittliche Spende in €"
        else:
            # Safe calculation of donation rate
            grouped = df_clean.groupby(col_to_rank, observed=False)
            total_counts = grouped.size()
            yes_counts = grouped['donated_at_all'].apply(lambda x: (x == "Ja").sum())
            rates = (yes_counts / total_counts * 100).fillna(0).reset_index()
            rates.columns = [col_to_rank, 'Wert']
            metric_df = rates
            x_title = "Spendenquote in %"
            
        # Merge values and sample sizes together
        ranking_df = pd.merge(metric_df, counts_df, on=col_to_rank)
        ranking_df['Wert'] = ranking_df['Wert'].round(2)
        
        # Format labels to show: Category (N=Sample Size)
        ranking_df['Label'] = ranking_df.apply(lambda r: f"{r[col_to_rank]} (N={r['N']})", axis=1)
        
        # Sort ascending because horizontal bar charts plot from bottom to top
        ranking_df = ranking_df.sort_values(by='Wert', ascending=True)
        
        # Draw the horizontal bar chart
        fig_rank = px.bar(
            ranking_df,
            x="Wert",
            y="Label",
            text="Wert",
            orientation='h',
            color="Wert",
            color_continuous_scale=px.colors.sequential.Teal
        )
        
        fig_rank.update_layout(
            xaxis_title=x_title,
            yaxis_title=None,
            showlegend=False,
            coloraxis_showscale=False,
            template="simple_white",
            height=max(400, len(ranking_df) * 35) # Automatically expands height for long lists (e.g., professions)
        )
        
        fig_rank.update_traces(
            texttemplate='%{text}', 
            textposition='outside'
        )
        
        st.plotly_chart(fig_rank, width='stretch')
        
    else:
        st.info("Keine Daten für dieses Ranking vorhanden.")