import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Dashboard SEO - Générateur de Graphiques",
    page_icon="📊",
    layout="wide"
)

# --- CONFIGURATION DES VALEURS PAR DÉFAUT ---
DEFAULT_COLORS = {
    'global_seo': '#2563EB', 'marque_clics': '#1E40AF', 'impressions_marque': '#3730A3',
    'hors_marque': '#2563EB', 'pie_marque': '#1E40AF', 'pie_hors_marque': '#A5B4FC',
    'evolution_positive': '#10B981', 'evolution_negative': '#EF4444'
}

# --- FONCTIONS DE TRAITEMENT DES DONNÉES ---

## CORRECTION MAJEURE: Assure la lecture correcte des dates sur chaque ligne
@st.cache_data
def load_data(uploaded_file):
    """Charge le fichier GSC et s'assure que la colonne de date est correctement formatée."""
    try:
        df = pd.read_excel(uploaded_file)
        required_cols = ['start_date', 'query', 'clicks', 'impressions']
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            st.error(f"Colonnes requises manquantes dans le fichier : {', '.join(missing)}")
            return None
        
        # Conversion cruciale et robuste de la colonne 'start_date'
        df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
        df.dropna(subset=['start_date'], inplace=True)
        if df.empty:
            st.error("Aucune date valide trouvée dans la colonne 'start_date'.")
            return None
        df['start_date'] = df['start_date'].dt.date
        
        # Assurer que les colonnes numériques le sont
        for col in ['clicks', 'impressions']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df
    except Exception as e:
        st.error(f"Impossible de lire le fichier. Erreur : {e}")
        return None

def is_marque_query(query, regex_pattern):
    """Vérifie si une requête correspond à la regex de marque."""
    if pd.isna(query) or not regex_pattern: return False
    try: return bool(re.search(regex_pattern, str(query), re.IGNORECASE))
    except re.error: return False

@st.cache_data
def process_data_for_periods(_df, periode_n_dates, periode_n1_dates, regex_pattern):
    """Filtre le dataframe pour les deux périodes et calcule toutes les métriques."""
    df = _df.copy()
    df['is_marque'] = df['query'].apply(lambda q: is_marque_query(q, regex_pattern))
    
    # Filtrage pour la Période N
    periode_n_df = df[(df['start_date'] >= periode_n_dates[0]) & (df['start_date'] <= periode_n_dates[1])]
    
    # Filtrage pour la Période N-1
    periode_n1_df = df[(df['start_date'] >= periode_n1_dates[0]) & (df['start_date'] <= periode_n1_dates[1])]
    
    # Calcul des métriques
    metrics = {
        'total_clics_n': periode_n_df['clicks'].sum(),
        'clics_marque_n': periode_n_df[periode_n_df['is_marque']]['clicks'].sum(),
        'clics_hors_marque_n': periode_n_df[~periode_n_df['is_marque']]['clicks'].sum(),
        'impressions_marque_n': periode_n_df[periode_n_df['is_marque']]['impressions'].sum(),
        
        'total_clics_n1': periode_n1_df['clicks'].sum(),
        'clics_marque_n1': periode_n1_df[periode_n1_df['is_marque']]['clicks'].sum(),
        'clics_hors_marque_n1': periode_n1_df[~periode_n1_df['is_marque']]['clicks'].sum(),
        'impressions_marque_n1': periode_n1_df[periode_n1_df['is_marque']]['impressions'].sum(),
        
        'nom_periode_n': f"{periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')}",
        'nom_periode_n1': f"{periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}"
    }
    return metrics

# --- FONCTIONS DE CRÉATION DE GRAPHIQUES (Factorisées et Stables) ---
def create_evolution_chart(metrics):
    COLORS = DEFAULT_COLORS
    def calc_evo(n, n1): return ((n - n1) / n1 * 100) if n1 > 0 else 0
    evolutions = [
        {'Métrique': 'Total Clics', 'Évolution': calc_evo(metrics['total_clics_n'], metrics['total_clics_n1'])},
        {'Métrique': 'Clics Marque', 'Évolution': calc_evo(metrics['clics_marque_n'], metrics['clics_marque_n1'])},
        {'Métrique': 'Clics Hors-Marque', 'Évolution': calc_evo(metrics['clics_hors_marque_n'], metrics['clics_hors_marque_n1'])},
        {'Métrique': 'Impressions Marque', 'Évolution': calc_evo(metrics['impressions_marque_n'], metrics['impressions_marque_n1'])}
    ]
    df_evo = pd.DataFrame(evolutions)
    bar_colors = [COLORS['evolution_positive'] if x >= 0 else COLORS['evolution_negative'] for x in df_evo['Évolution']]
    fig = go.Figure(data=[go.Bar(x=df_evo['Métrique'], y=df_evo['Évolution'], marker_color=bar_colors, text=[f"{x:+.1f}%" for x in df_evo['Évolution']], textposition='auto', textfont=dict(size=14, color='white'))])
    fig.update_layout(title="Synthèse des Évolutions (%)", yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black'), height=500)
    return fig

def create_pie_charts(metrics):
    COLORS = DEFAULT_COLORS
    def create_single_pie(clics_m, clics_hm, title):
        total = clics_m + clics_hm
        pct_m = (clics_m / total * 100) if total > 0 else 0
        pct_hm = (clics_hm / total * 100) if total > 0 else 0
        fig = go.Figure(data=[go.Pie(labels=[f'Hors-Marque<br>{clics_hm:,} ({pct_hm:.1f}%)', f'Marque<br>{clics_m:,} ({pct_m:.1f}%)'], values=[clics_hm, clics_m], marker_colors=[COLORS['pie_hors_marque'], COLORS['pie_marque']], hole=0.4, textinfo='label', textposition='auto')])
        fig.update_layout(title=title, height=450)
        return fig
    fig_n1 = create_single_pie(metrics['clics_marque_n1'], metrics['clics_hors_marque_n1'], f"Répartition N-1: {metrics['nom_periode_n1']}")
    fig_n = create_single_pie(metrics['clics_marque_n'], metrics['clics_hors_marque_n'], f"Répartition N: {metrics['nom_periode_n']}")
    return fig_n, fig_n1

def create_bar_chart(metrics, data_key, color, title, yaxis_title):
    fig = go.Figure(data=[go.Bar(
        x=[f"Période N-1<br>{metrics['nom_periode_n1']}", f"Période N<br>{metrics['nom_periode_n']}"],
        y=[metrics[f'{data_key}_n1'], metrics[f'{data_key}_n']],
        marker_color=color, text=[f"{metrics[f'{data_key}_n1']:,}", f"{metrics[f'{data_key}_n']:,}"],
        textposition='auto', textfont=dict(size=14, color='white')
    )])
    fig.update_layout(title=title, yaxis_title=yaxis_title, height=500)
    return fig

# --- INTERFACE UTILISATEUR (UI) ---
def main():
    st.title("📊 Dashboard SEO - Analyse de Périodes")
    st.markdown("Chargez un fichier de données GSC et définissez deux périodes pour les comparer.")

    # --- 1. Configuration ---
    st.markdown("### 1. Configuration de la Marque")
    regex_pattern = st.text_input("Regex pour identifier les requêtes de marque", value="melvita", help="Ex: 'marque1|marque2'")
    
    # --- 2. Upload du fichier ---
    st.markdown("### 2. Import des Données")
    uploaded_file = st.file_uploader("Chargez votre export Google Search Console (Excel)", type=['xlsx', 'xls'])

    if uploaded_file:
        df = load_data(uploaded_file)
        if df is None:
            st.stop()
        
        st.success(f"Fichier chargé avec succès! ({len(df):,} lignes)")
        
        min_date = df['start_date'].min()
        max_date = df['start_date'].max()
        st.info(f"Période couverte par le fichier : du **{min_date.strftime('%d/%m/%Y')}** au **{max_date.strftime('%d/%m/%Y')}**.")
        
        # --- 3. Sélection des dates ---
        st.markdown("### 3. Sélection des Périodes de Comparaison")
        
        # Proposer des dates par défaut intelligentes (ex: les 2 derniers trimestres)
        default_end_n = max_date
        default_start_n = (default_end_n.replace(day=1) - relativedelta(months=2)).replace(day=1)
        default_end_n1 = default_start_n - timedelta(days=1)
        default_start_n1 = (default_end_n1.replace(day=1) - relativedelta(months=2)).replace(day=1)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Période N (actuelle)")
            start_n = st.date_input("Date de début N", value=default_start_n, min_value=min_date, max_value=max_date)
            end_n = st.date_input("Date de fin N", value=default_end_n, min_value=min_date, max_value=max_date)
        with col2:
            st.markdown("#### Période N-1 (précédente)")
            start_n1 = st.date_input("Date de début N-1", value=default_start_n1, min_value=min_date, max_value=max_date)
            end_n1 = st.date_input("Date de fin N-1", value=default_end_n1, min_value=min_date, max_value=max_date)
            
        if start_n > end_n or start_n1 > end_n1:
            st.error("La date de début ne peut pas être après la date de fin.")
            st.stop()
        
        # --- 4. Traitement et Affichage ---
        st.markdown("---")
        st.header("🚀 Résultats de la Comparaison")

        metrics = process_data_for_periods(df, (start_n, end_n), (start_n1, end_n1), regex_pattern)
        
        if metrics['total_clics_n'] == 0 and metrics['total_clics_n1'] == 0:
            st.warning("Aucune donnée trouvée pour les périodes sélectionnées. Veuillez ajuster les dates.")
            st.stop()
        
        # Affichage des graphiques
        st.plotly_chart(create_evolution_chart(metrics), use_container_width=True)
        
        fig_n, fig_n1 = create_pie_charts(metrics)
        pie_col1, pie_col2 = st.columns(2)
        with pie_col1:
            st.plotly_chart(fig_n1, use_container_width=True)
        with pie_col2:
            st.plotly_chart(fig_n, use_container_width=True)
        
        COLORS = DEFAULT_COLORS
        st.plotly_chart(create_bar_chart(metrics, 'total_clics', COLORS['global_seo'], "Trafic SEO Global (Clics)", "Clics"), use_container_width=True)
        st.plotly_chart(create_bar_chart(metrics, 'clics_marque', COLORS['marque_clics'], "Trafic SEO Marque (Clics)", "Clics"), use_container_width=True)
        st.plotly_chart(create_bar_chart(metrics, 'clics_hors_marque', COLORS['hors_marque'], "Trafic SEO Hors-Marque (Clics)", "Clics"), use_container_width=True)
        st.plotly_chart(create_bar_chart(metrics, 'impressions_marque', COLORS['impressions_marque'], "Impressions SEO Marque", "Impressions"), use_container_width=True)

if __name__ == "__main__":
    main()
