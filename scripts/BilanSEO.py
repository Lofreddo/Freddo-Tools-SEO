import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Dashboard SEO - Comparateur de Fichiers",
    page_icon="📊",
    layout="wide"
)

# --- CONFIGURATION DES VALEURS PAR DÉFAUT (COULEURS, ETC.) ---
DEFAULT_COLORS = {
    'global_seo': '#2563EB', 'marque_clics': '#1E40AF', 'impressions_marque': '#3730A3',
    'hors_marque': '#2563EB', 'pie_marque': '#1E40AF', 'pie_hors_marque': '#A5B4FC',
    'evolution_positive': '#10B981', 'evolution_negative': '#EF4444'
}

def get_colors():
    """Gère les couleurs personnalisées via le session_state."""
    if 'custom_colors' not in st.session_state:
        st.session_state.custom_colors = DEFAULT_COLORS.copy()
    return st.session_state.custom_colors

# --- FONCTIONS PRINCIPALES DE TRAITEMENT ---

def is_marque_query(query, regex_pattern):
    """Vérifie si une requête correspond à la regex de marque."""
    if pd.isna(query) or not regex_pattern:
        return False
    try:
        return bool(re.search(regex_pattern, str(query), re.IGNORECASE))
    except re.error:
        return False

def process_gsc_file(uploaded_file, regex_pattern):
    """
    Fonction centrale conçue spécifiquement pour votre format de fichier.
    - Lit les dates en A1 et A2.
    - Utilise la ligne 3 comme en-têtes.
    - Calcule les métriques pour l'ensemble du fichier.
    """
    if uploaded_file is None:
        return None

    try:
        # Lire le fichier sans en-tête pour accéder aux premières lignes
        df = pd.read_excel(uploaded_file, header=None)
        
        # 1. Extraire les dates des deux premières lignes (cellules A1 et A2)
        start_date = pd.to_datetime(df.iloc[0, 0]).date()
        end_date = pd.to_datetime(df.iloc[1, 0]).date()
        period_name = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

        # 2. Définir les en-têtes de colonnes à partir de la troisième ligne (index 2)
        df.columns = df.iloc[2]
        
        # 3. Supprimer les 3 premières lignes (dates et en-tête) pour ne garder que les données
        data_df = df.iloc[3:].reset_index(drop=True)
        
        # 4. Vérifier que les colonnes nécessaires sont présentes
        required_cols = ['query', 'clicks', 'impressions']
        if not all(col in data_df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in data_df.columns]
            st.error(f"Colonnes requises manquantes dans le fichier '{uploaded_file.name}': {', '.join(missing)}")
            return None
            
        # 5. S'assurer que les clics et impressions sont des nombres
        data_df['clicks'] = pd.to_numeric(data_df['clicks'], errors='coerce').fillna(0)
        data_df['impressions'] = pd.to_numeric(data_df['impressions'], errors='coerce').fillna(0)
        
        # 6. Calculer les métriques
        data_df['is_marque'] = data_df['query'].apply(lambda q: is_marque_query(q, regex_pattern))
        
        metrics = {
            'period_name': period_name,
            'total_clics': data_df['clicks'].sum(),
            'total_impressions': data_df['impressions'].sum(),
            'clics_marque': data_df[data_df['is_marque']]['clicks'].sum(),
            'clics_hors_marque': data_df[~data_df['is_marque']]['clicks'].sum(),
            'impressions_marque': data_df[data_df['is_marque']]['impressions'].sum()
        }
        
        return metrics

    except Exception as e:
        st.error(f"Erreur lors du traitement du fichier '{uploaded_file.name}': {e}")
        st.info("Veuillez vérifier que le fichier a bien les dates en A1 et A2 et les données à partir de la ligne 4.")
        return None


# --- FONCTIONS DE CRÉATION DE GRAPHIQUES ---

def create_evolution_chart(metrics_n, metrics_n1):
    """Crée le graphique de synthèse des évolutions."""
    COLORS = get_colors()
    
    def calc_evo(n, n1):
        return ((n - n1) / n1 * 100) if n1 > 0 else 0
        
    evolutions = [
        {'Métrique': 'Total Clics', 'Évolution': calc_evo(metrics_n['total_clics'], metrics_n1['total_clics'])},
        {'Métrique': 'Clics Marque', 'Évolution': calc_evo(metrics_n['clics_marque'], metrics_n1['clics_marque'])},
        {'Métrique': 'Clics Hors-Marque', 'Évolution': calc_evo(metrics_n['clics_hors_marque'], metrics_n1['clics_hors_marque'])},
        {'Métrique': 'Impressions Marque', 'Évolution': calc_evo(metrics_n['impressions_marque'], metrics_n1['impressions_marque'])}
    ]
    df_evo = pd.DataFrame(evolutions)
    bar_colors = [COLORS['evolution_positive'] if x >= 0 else COLORS['evolution_negative'] for x in df_evo['Évolution']]
    
    fig = go.Figure(data=[go.Bar(
        x=df_evo['Métrique'], y=df_evo['Évolution'], marker_color=bar_colors,
        text=[f"{x:+.1f}%" for x in df_evo['Évolution']], textposition='auto', textfont=dict(size=14, color='white')
    )])
    fig.update_layout(
        title="Synthèse des Évolutions (%)",
        yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black'),
        height=500
    )
    return fig

def create_pie_charts(metrics_n, metrics_n1):
    """Crée les deux graphiques camemberts."""
    COLORS = get_colors()
    
    def create_single_pie(metrics, title):
        total = metrics['total_clics']
        pct_marque = (metrics['clics_marque'] / total * 100) if total > 0 else 0
        pct_hors_marque = (metrics['clics_hors_marque'] / total * 100) if total > 0 else 0
        
        fig = go.Figure(data=[go.Pie(
            labels=[f'Hors-Marque<br>{metrics["clics_hors_marque"]:,} ({pct_hors_marque:.1f}%)', 
                    f'Marque<br>{metrics["clics_marque"]:,} ({pct_marque:.1f}%)'],
            values=[metrics['clics_hors_marque'], metrics['clics_marque']],
            marker_colors=[COLORS['pie_hors_marque'], COLORS['pie_marque']],
            hole=0.4, textinfo='label', textposition='auto'
        )])
        fig.update_layout(title=title, height=450)
        return fig

    fig_n1 = create_single_pie(metrics_n1, f"Répartition N-1: {metrics_n1['period_name']}")
    fig_n = create_single_pie(metrics_n, f"Répartition N: {metrics_n['period_name']}")
    return fig_n, fig_n1

def create_bar_chart(metrics_n, metrics_n1, data_key, color, title, yaxis_title):
    """Crée un graphique en barres de comparaison générique."""
    fig = go.Figure(data=[
        go.Bar(
            x=[f"Période N-1<br>{metrics_n1['period_name']}", f"Période N<br>{metrics_n['period_name']}"],
            y=[metrics_n1[data_key], metrics_n[data_key]],
            marker_color=color,
            text=[f"{metrics_n1[data_key]:,}", f"{metrics_n[data_key]:,}"],
            textposition='auto',
            textfont=dict(size=14, color='white')
        )
    ])
    fig.update_layout(title=title, yaxis_title=yaxis_title, height=500)
    return fig

# --- INTERFACE UTILISATEUR (UI) ---

def main():
    st.title("📊 Dashboard SEO - Comparateur de Périodes")
    st.markdown("Cette application compare deux périodes de données SEO en se basant sur deux fichiers distincts.")
    st.info("**Mode d'emploi :** Téléchargez un fichier pour la période actuelle (N) et un autre pour la période précédente (N-1).")

    # --- 1. Configuration de la Regex ---
    st.markdown("### 1. Configuration de la Marque")
    regex_pattern = st.text_input(
        "Regex pour identifier les requêtes de marque",
        value="weefin|wee fin",
        help="Utilisez `|` pour séparer les termes. Ex: 'ma_marque|ma marque|mon_autre_produit'"
    )
    if not regex_pattern:
        st.warning("Veuillez saisir une regex pour continuer.")
        st.stop()
    try:
        re.compile(regex_pattern)
    except re.error:
        st.error("Regex invalide. Veuillez la corriger.")
        st.stop()
    
    # --- 2. Téléchargement des Fichiers ---
    st.markdown("### 2. Téléchargement des Fichiers de Périodes")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Période N (actuelle)")
        uploaded_file_n = st.file_uploader("Télécharger le fichier pour la période N", type=['xlsx', 'xls'], key="file_n")

    with col2:
        st.markdown("#### Période N-1 (précédente)")
        uploaded_file_n1 = st.file_uploader("Télécharger le fichier pour la période N-1", type=['xlsx', 'xls'], key="file_n1")
        
    # --- 3. Traitement et Affichage ---
    if uploaded_file_n and uploaded_file_n1:
        st.markdown("---")
        st.header("🚀 Résultats de la Comparaison")

        # Traitement des deux fichiers
        metrics_n = process_gsc_file(uploaded_file_n, regex_pattern)
        metrics_n1 = process_gsc_file(uploaded_file_n1, regex_pattern)

        if metrics_n and metrics_n1:
            COLORS = get_colors()
            
            # Affichage des graphiques
            st.plotly_chart(create_evolution_chart(metrics_n, metrics_n1), use_container_width=True)
            
            fig_n, fig_n1 = create_pie_charts(metrics_n, metrics_n1)
            pie_col1, pie_col2 = st.columns(2)
            with pie_col1:
                st.plotly_chart(fig_n1, use_container_width=True)
            with pie_col2:
                st.plotly_chart(fig_n, use_container_width=True)
            
            st.plotly_chart(create_bar_chart(metrics_n, metrics_n1, 'total_clics', COLORS['global_seo'], "Trafic SEO Global (Clics)", "Clics"), use_container_width=True)
            st.plotly_chart(create_bar_chart(metrics_n, metrics_n1, 'clics_marque', COLORS['marque_clics'], "Trafic SEO Marque (Clics)", "Clics"), use_container_width=True)
            st.plotly_chart(create_bar_chart(metrics_n, metrics_n1, 'clics_hors_marque', COLORS['hors_marque'], "Trafic SEO Hors-Marque (Clics)", "Clics"), use_container_width=True)
            st.plotly_chart(create_bar_chart(metrics_n, metrics_n1, 'impressions_marque', COLORS['impressions_marque'], "Impressions SEO Marque", "Impressions"), use_container_width=True)
        else:
            st.error("Un ou deux fichiers n'ont pas pu être traités. Veuillez vérifier leur format.")

if __name__ == "__main__":
    main()
