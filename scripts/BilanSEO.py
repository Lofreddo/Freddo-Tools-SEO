import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
import calendar
import io

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Dashboard SEO - Générateur de Graphiques",
    page_icon="📊",
    layout="wide"
)

# --- CONFIGURATION DES VALEURS PAR DÉFAUT ---

# Couleurs par défaut du dashboard
DEFAULT_COLORS = {
    'global_seo': '#2563EB', 'marque_clics': '#1E40AF', 'impressions_marque': '#3730A3',
    'hors_marque': '#2563EB', 'pie_marque': '#1E40AF', 'pie_hors_marque': '#A5B4FC',
    'evolution_positive': '#10B981', 'evolution_negative': '#EF4444',
    'secondary_light': '#A5B4FC', 'secondary_dark': '#2563EB'
}

# Options de mise en page par défaut
DEFAULT_LAYOUT_OPTIONS = {
    'font_family': 'Arial, sans-serif',
    'chart_height': 500,
    'plot_bgcolor': '#FFFFFF',
    'show_text_on_bars': True,
    'legend_orientation': 'h' # h: horizontal, v: vertical
}

# Liste des polices disponibles
FONT_OPTIONS = [
    'Arial, sans-serif', 'Verdana, sans-serif', 'Tahoma, sans-serif', 
    'Trebuchet MS, sans-serif', 'Georgia, serif', 'Times New Roman, serif', 
    'Courier New, monospace'
]

# --- GESTION DE L'ÉTAT DE SESSION (SESSION STATE) ---

def get_colors():
    """Récupère les couleurs depuis la session ou utilise les couleurs par défaut."""
    if 'custom_colors' not in st.session_state:
        st.session_state.custom_colors = DEFAULT_COLORS.copy()
    return st.session_state.custom_colors

def get_layout_options():
    """Récupère les options de mise en page depuis la session ou les valeurs par défaut."""
    if 'custom_layout' not in st.session_state:
        st.session_state.custom_layout = DEFAULT_LAYOUT_OPTIONS.copy()
    return st.session_state.custom_layout

# --- FONCTIONS UTILITAIRES ET TRAITEMENT DES DONNÉES ---

@st.cache_data
def load_data(uploaded_file):
    """Charge et pré-traite les données du fichier Excel. La mise en cache accélère les re-runs."""
    df = pd.read_excel(uploaded_file)
    required_cols = ['start_date', 'query', 'clicks', 'impressions']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"Colonnes requises manquantes dans le fichier : {', '.join(missing_cols)}")
        return None
    
    # Conversion de la date une seule fois
    df['start_date'] = pd.to_datetime(df['start_date']).dt.date
    return df

def is_marque_query(query, regex_pattern):
    """Identifie les requêtes de marque avec la regex personnalisée."""
    if pd.isna(query) or not regex_pattern:
        return False
    try:
        return bool(re.search(regex_pattern, str(query), re.IGNORECASE))
    except re.error:
        return False

def get_predefined_periods():
    """Retourne les périodes prédéfinies basées sur la date actuelle."""
    today = datetime.now().date()
    return {
        "7_derniers_jours": ("7 derniers jours", (today - timedelta(days=6), today), (today - timedelta(days=13), today - timedelta(days=7))),
        "28_derniers_jours": ("28 derniers jours", (today - timedelta(days=27), today), (today - timedelta(days=55), today - timedelta(days=28))),
        "3_derniers_mois": ("3 derniers mois", (today - timedelta(days=89), today), (today - timedelta(days=179), today - timedelta(days=90))),
        "6_derniers_mois": ("6 derniers mois", (today - timedelta(days=179), today), (today - timedelta(days=359), today - timedelta(days=180))),
    }

def format_period_name(start_date, end_date):
    """Formate le nom de la période pour affichage."""
    return f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

@st.cache_data
def process_data_for_periods(_df, periode_n_dates, periode_n1_dates, regex_pattern):
    """Traite les données pour les périodes données. Utilise le DataFrame mis en cache."""
    df = _df.copy() # Évite de modifier le cache
    df['is_marque'] = df['query'].apply(lambda q: is_marque_query(q, regex_pattern))
    
    periode_n = df[(df['start_date'] >= periode_n_dates[0]) & (df['start_date'] <= periode_n_dates[1])]
    periode_n1 = df[(df['start_date'] >= periode_n1_dates[0]) & (df['start_date'] <= periode_n1_dates[1])]
    
    metrics = {
        'total_clics_n1': periode_n1['clicks'].sum(),
        'total_clics_n': periode_n['clicks'].sum(),
        'clics_marque_n1': periode_n1[periode_n1['is_marque']]['clicks'].sum(),
        'clics_marque_n': periode_n[periode_n['is_marque']]['clicks'].sum(),
        'clics_hors_marque_n1': periode_n1[~periode_n1['is_marque']]['clicks'].sum(),
        'clics_hors_marque_n': periode_n[~periode_n['is_marque']]['clicks'].sum(),
        'impressions_marque_n1': periode_n1[periode_n1['is_marque']]['impressions'].sum(),
        'impressions_marque_n': periode_n[periode_n['is_marque']]['impressions'].sum(),
        'total_impressions_n1': periode_n1['impressions'].sum(),
        'total_impressions_n': periode_n['impressions'].sum(),
        'nom_periode_n1': format_period_name(periode_n1_dates[0], periode_n1_dates[1]),
        'nom_periode_n': format_period_name(periode_n_dates[0], periode_n_dates[1])
    }
    return metrics

@st.cache_data
def process_monthly_data(_df, year_n, year_n1, regex_pattern):
    """Traite les données pour une comparaison mois par mois. Utilise le DataFrame mis en cache."""
    df = _df.copy()
    df['month'] = pd.to_datetime(df['start_date']).dt.month
    df['year'] = pd.to_datetime(df['start_date']).dt.year
    df['is_marque'] = df['query'].apply(lambda q: is_marque_query(q, regex_pattern))
    
    data_n = df[df['year'] == year_n]
    data_n1 = df[df['year'] == year_n1]
    
    months_n = set(data_n['month'].unique())
    months_n1 = set(data_n1['month'].unique())
    comparable_months = sorted(list(months_n.intersection(months_n1)))
    
    if not comparable_months: return None
        
    month_names = {1: 'Jan', 2: 'Fév', 3: 'Mar', 4: 'Avr', 5: 'Mai', 6: 'Juin', 7: 'Juil', 8: 'Août', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Déc'}
    
    monthly_data = {'months': [month_names[m] for m in comparable_months], 'year_n': year_n, 'year_n1': year_n1}
    metrics_to_calc = ['total_clics', 'clics_marque', 'clics_hors_marque', 'impressions_marque', 'total_impressions']
    
    for metric in metrics_to_calc:
        metric_key_n, metric_key_n1 = f"{metric}_n", f"{metric}_n1"
        monthly_data[metric_key_n], monthly_data[metric_key_n1] = [], []
        
        is_marque_filter = 'is_marque' if 'marque' in metric else None
        
        for month in comparable_months:
            # Année N
            month_data_n = data_n[data_n['month'] == month]
            if is_marque_filter:
                filter_cond = month_data_n[is_marque_filter] if 'hors' not in metric else ~month_data_n[is_marque_filter]
                monthly_data[metric_key_n].append(month_data_n[filter_cond]['clicks' if 'clics' in metric else 'impressions'].sum())
            else:
                monthly_data[metric_key_n].append(month_data_n['clicks' if 'clics' in metric else 'impressions'].sum())
            
            # Année N-1
            month_data_n1 = data_n1[data_n1['month'] == month]
            if is_marque_filter:
                filter_cond = month_data_n1[is_marque_filter] if 'hors' not in metric else ~month_data_n1[is_marque_filter]
                monthly_data[metric_key_n1].append(month_data_n1[filter_cond]['clicks' if 'clics' in metric else 'impressions'].sum())
            else:
                monthly_data[metric_key_n1].append(month_data_n1['clicks' if 'clics' in metric else 'impressions'].sum())
    
    monthly_data['months_count'] = len(comparable_months)
    return monthly_data


# --- FONCTIONS DE CRÉATION DE GRAPHIQUES (FACTORISÉES) ---

def create_base_layout(title, yaxis_title, period_type=""):
    """Crée une mise en page de base pour les graphiques Plotly."""
    LAYOUT_OPTIONS = get_layout_options()
    return go.Layout(
        title=f"{title} - {period_type}",
        xaxis_title="Période",
        yaxis_title=yaxis_title,
        font=dict(size=12, family=LAYOUT_OPTIONS['font_family']),
        height=LAYOUT_OPTIONS['chart_height'],
        plot_bgcolor=LAYOUT_OPTIONS['plot_bgcolor'],
        showlegend=False
    )

def create_comparison_bar_chart(metrics, y_key, color, title, period_type, yaxis_title="Clics"):
    """Fonction helper pour créer des graphiques en barres de comparaison N vs N-1."""
    LAYOUT_OPTIONS = get_layout_options()
    fig = go.Figure()
    
    y_values = [metrics[f'{y_key}_n1'], metrics[f'{y_key}_n']]
    text_values = [f"{v:,}" for v in y_values] if LAYOUT_OPTIONS['show_text_on_bars'] else None
    
    fig.add_trace(go.Bar(
        x=[f"Période N-1<br>{metrics['nom_periode_n1']}", f"Période N<br>{metrics['nom_periode_n']}"],
        y=y_values,
        marker_color=color,
        text=text_values,
        textposition='auto',
        textfont=dict(size=14, color='white')
    ))
    fig.update_layout(create_base_layout(title, yaxis_title, period_type))
    return fig

def create_monthly_bar_chart(monthly_data, y_key, color_n, color_n1, title, yaxis_title="Clics"):
    """Fonction helper pour les graphiques de comparaison mensuelle."""
    LAYOUT_OPTIONS = get_layout_options()
    COLORS = get_colors()
    fig = go.Figure()

    text_n1 = [f"{v:,}" for v in monthly_data[f'{y_key}_n1']] if LAYOUT_OPTIONS['show_text_on_bars'] else None
    text_n = [f"{v:,}" for v in monthly_data[f'{y_key}_n']] if LAYOUT_OPTIONS['show_text_on_bars'] else None

    fig.add_trace(go.Bar(
        x=monthly_data['months'], y=monthly_data[f'{y_key}_n1'], name=f"{monthly_data['year_n1']}",
        marker_color=color_n1, text=text_n1, textposition='auto', textfont=dict(size=11)
    ))
    fig.add_trace(go.Bar(
        x=monthly_data['months'], y=monthly_data[f'{y_key}_n'], name=f"{monthly_data['year_n']}",
        marker_color=color_n, text=text_n, textposition='auto', textfont=dict(size=11)
    ))
    fig.update_layout(
        create_base_layout(f"{title} - {monthly_data['year_n1']} vs {monthly_data['year_n']}", yaxis_title, f"{monthly_data['months_count']} mois comparable(s)"),
        barmode='group',
        showlegend=True,
        legend=dict(orientation=LAYOUT_OPTIONS['legend_orientation'], yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def create_evolution_chart(metrics, period_type=""):
    """Génère le graphique de synthèse des évolutions."""
    COLORS = get_colors()
    LAYOUT_OPTIONS = get_layout_options()
    evolutions = []
    
    def calc_evo(n, n1):
        return ((n - n1) / n1 * 100) if n1 > 0 else 0

    evolutions.append({'Métrique': 'Total Clics', 'Évolution': calc_evo(metrics['total_clics_n'], metrics['total_clics_n1'])})
    evolutions.append({'Métrique': 'Clics Marque', 'Évolution': calc_evo(metrics['clics_marque_n'], metrics['clics_marque_n1'])})
    evolutions.append({'Métrique': 'Clics Hors-Marque', 'Évolution': calc_evo(metrics['clics_hors_marque_n'], metrics['clics_hors_marque_n1'])})
    evolutions.append({'Métrique': 'Impressions Marque', 'Évolution': calc_evo(metrics['impressions_marque_n'], metrics['impressions_marque_n1'])})
    
    df_evo = pd.DataFrame(evolutions)
    bar_colors = [COLORS['evolution_positive'] if x >= 0 else COLORS['evolution_negative'] for x in df_evo['Évolution']]
    
    fig = go.Figure(data=[go.Bar(
        x=df_evo['Métrique'], y=df_evo['Évolution'], marker_color=bar_colors,
        text=[f"{x:+.1f}%" for x in df_evo['Évolution']], textposition='auto', textfont=dict(size=14, color='white')
    )])
    fig.update_layout(
        create_base_layout("Synthèse des Évolutions (%)", "Évolution (%)", f"Période N vs N-1 - {period_type}"),
        yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black')
    )
    return fig

def create_pie_charts(metrics, period_type=""):
    """Génère les deux graphiques camemberts pour la comparaison."""
    COLORS = get_colors()
    LAYOUT_OPTIONS = get_layout_options()
    
    def create_single_pie(clics_marque, clics_hors_marque, title):
        total = clics_marque + clics_hors_marque
        pct_marque = (clics_marque / total * 100) if total > 0 else 0
        pct_hors_marque = (clics_hors_marque / total * 100) if total > 0 else 0
        
        fig = go.Figure(data=[go.Pie(
            labels=[f'Hors-Marque<br>{clics_hors_marque:,} ({pct_hors_marque:.1f}%)', f'Marque<br>{clics_marque:,} ({pct_marque:.1f}%)'],
            values=[clics_hors_marque, clics_marque],
            marker_colors=[COLORS['pie_hors_marque'], COLORS['pie_marque']],
            hole=0.4, textinfo='label', textposition='auto', textfont=dict(size=12, family=LAYOUT_OPTIONS['font_family'])
        )])
        fig.update_layout(
            title=title,
            height=LAYOUT_OPTIONS['chart_height'] - 50,
            font=dict(size=10, family=LAYOUT_OPTIONS['font_family'])
        )
        return fig

    fig1 = create_single_pie(metrics['clics_marque_n1'], metrics['clics_hors_marque_n1'], f"Répartition N-1: {metrics['nom_periode_n1']}")
    fig2 = create_single_pie(metrics['clics_marque_n'], metrics['clics_hors_marque_n'], f"Répartition N: {metrics['nom_periode_n']}")
    
    return fig1, fig2

# --- INTERFACE UTILISATEUR (UI) ---

def show_customization_options():
    """Affiche les options de personnalisation dans la barre latérale."""
    st.sidebar.title("🎨 Options de Personnalisation")

    with st.sidebar.expander("Mise en page des graphiques", expanded=True):
        LAYOUT_OPTIONS = get_layout_options()
        LAYOUT_OPTIONS['font_family'] = st.selectbox("Police de caractères", FONT_OPTIONS, index=FONT_OPTIONS.index(LAYOUT_OPTIONS['font_family']))
        LAYOUT_OPTIONS['chart_height'] = st.slider("Hauteur des graphiques (px)", 400, 1000, LAYOUT_OPTIONS['chart_height'])
        LAYOUT_OPTIONS['plot_bgcolor'] = st.color_picker("Couleur de fond des graphiques", LAYOUT_OPTIONS['plot_bgcolor'])
        LAYOUT_OPTIONS['show_text_on_bars'] = st.toggle("Afficher les valeurs sur les barres", value=LAYOUT_OPTIONS['show_text_on_bars'])
        LAYOUT_OPTIONS['legend_orientation'] = 'h' if st.radio("Position de la légende (mensuel)", ["Horizontale (haut)", "Verticale (droite)"], index=0 if LAYOUT_OPTIONS['legend_orientation'] == 'h' else 1) == "Horizontale (haut)" else 'v'
        st.session_state.custom_layout = LAYOUT_OPTIONS

    with st.sidebar.expander("Couleurs des graphiques", expanded=False):
        COLORS = get_colors()
        color_keys = list(DEFAULT_COLORS.keys())
        for key in color_keys:
            label = key.replace('_', ' ').replace('evolution', 'Évolution').title()
            COLORS[key] = st.color_picker(label, COLORS[key])
        
        st.session_state.custom_colors = COLORS
        if st.button("Réinitialiser les couleurs"):
            st.session_state.custom_colors = DEFAULT_COLORS.copy()
            st.rerun()

def main():
    st.title("📊 Dashboard SEO - Générateur de Graphiques")
    st.markdown("**Analysez vos performances SEO sur différentes périodes avec des visualisations personnalisées.**")

    # Options de personnalisation dans la barre latérale
    show_customization_options()
    
    st.markdown("---")
    st.markdown("### 🏷️ 1. Configuration de la Marque")
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

    st.markdown("### 📂 2. Import des Données")
    uploaded_file = st.file_uploader(
        "Uploadez votre fichier Google Search Console (Excel)",
        type=['xlsx', 'xls']
    )
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is None:
            st.stop()
        
        st.success(f"Fichier chargé avec succès! ({len(df):,} lignes)")
        
        st.markdown("### 📊 3. Type d'Analyse")
        analysis_type = st.radio(
            "Choisissez le type de comparaison :",
            ["Comparaison par Blocs/Périodes", "Comparaison Mensuelle (Année N vs N-1)"],
            horizontal=True,
            help="**Blocs**: Compare deux périodes distinctes (ex: Q2 vs Q1). **Mensuelle**: Compare chaque mois d'une année à son équivalent de l'année précédente."
        )
        
        st.markdown("### 📅 4. Sélection des Périodes")
        
        if analysis_type == "Comparaison par Blocs/Périodes":
            period_options = get_predefined_periods()
            selected_key = st.selectbox(
                "Choisissez une période prédéfinie ou personnalisez",
                list(period_options.keys()) + ["Personnalisée"],
                format_func=lambda k: period_options[k][0] if k != "Personnalisée" else "Personnalisée",
                index=1 # 28 jours par défaut
            )
            
            if selected_key == "Personnalisée":
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("##### Période N (actuelle)")
                    start_n = st.date_input("Date de début N", datetime(2025, 4, 1).date())
                    end_n = st.date_input("Date de fin N", datetime(2025, 6, 30).date())
                with col2:
                    st.markdown("##### Période N-1 (précédente)")
                    start_n1 = st.date_input("Date de début N-1", datetime(2025, 1, 1).date())
                    end_n1 = st.date_input("Date de fin N-1", datetime(2025, 3, 31).date())
                periode_n_dates, periode_n1_dates = (start_n, end_n), (start_n1, end_n1)
                period_type = "Personnalisée"
            else:
                period_type, periode_n_dates, periode_n1_dates = period_options[selected_key]
                st.info(f"**Période N**: {format_period_name(*periode_n_dates)} | **Période N-1**: {format_period_name(*periode_n1_dates)}")

            metrics = process_data_for_periods(df, periode_n_dates, periode_n1_dates, regex_pattern)
            
            if metrics['total_clics_n'] == 0 and metrics['total_clics_n1'] == 0:
                st.warning("Aucune donnée trouvée pour les périodes sélectionnées.")
                st.stop()
            
            # Affichage des graphiques pour l'analyse par blocs
            st.markdown("---")
            st.header("🚀 Résultats de l'Analyse par Blocs")
            
            # Création et affichage des graphiques
            COLORS = get_colors()
            st.plotly_chart(create_evolution_chart(metrics, period_type), use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                pie1, _ = create_pie_charts(metrics, period_type)
                st.plotly_chart(pie1, use_container_width=True)
            with col2:
                _, pie2 = create_pie_charts(metrics, period_type)
                st.plotly_chart(pie2, use_container_width=True)

            st.plotly_chart(create_comparison_bar_chart(metrics, 'total_clics', COLORS['global_seo'], "Trafic SEO Global", period_type), use_container_width=True)
            st.plotly_chart(create_comparison_bar_chart(metrics, 'clics_marque', COLORS['marque_clics'], "Trafic SEO Marque", period_type), use_container_width=True)
            st.plotly_chart(create_comparison_bar_chart(metrics, 'clics_hors_marque', COLORS['hors_marque'], "Trafic SEO Hors-Marque", period_type), use_container_width=True)
            st.plotly_chart(create_comparison_bar_chart(metrics, 'impressions_marque', COLORS['impressions_marque'], "Impressions SEO Marque", period_type, yaxis_title="Impressions"), use_container_width=True)
        
        else: # Analyse Mensuelle
            current_year = datetime.now().year
            selected_year = st.selectbox("Choisissez l'année N :", range(current_year + 1, current_year - 5, -1), index=1)
            previous_year = selected_year - 1
            st.info(f"Comparaison de chaque mois de **{selected_year}** avec le même mois de **{previous_year}**.")
            
            monthly_data = process_monthly_data(df, selected_year, previous_year, regex_pattern)

            if not monthly_data or monthly_data['months_count'] == 0:
                st.warning(f"Aucun mois comparable trouvé entre {previous_year} et {selected_year}. Assurez-vous que votre fichier contient des données pour ces deux années.")
                st.stop()
            
            st.success(f"Analyse sur **{monthly_data['months_count']} mois comparable(s)** : {', '.join(monthly_data['months'])}")
            
            # Affichage des graphiques pour l'analyse mensuelle
            st.markdown("---")
            st.header("🚀 Résultats de l'Analyse Mensuelle")
            
            COLORS = get_colors()
            st.plotly_chart(create_monthly_bar_chart(monthly_data, 'total_clics', COLORS['secondary_dark'], COLORS['secondary_light'], "Trafic SEO Global par Mois"), use_container_width=True)
            st.plotly_chart(create_monthly_bar_chart(monthly_data, 'clics_marque', COLORS['marque_clics'], COLORS['secondary_light'], "Trafic SEO Marque par Mois"), use_container_width=True)
            st.plotly_chart(create_monthly_bar_chart(monthly_data, 'clics_hors_marque', COLORS['hors_marque'], COLORS['secondary_light'], "Trafic SEO Hors-Marque par Mois"), use_container_width=True)
            st.plotly_chart(create_monthly_bar_chart(monthly_data, 'impressions_marque', COLORS['impressions_marque'], COLORS['secondary_light'], "Impressions SEO Marque par Mois", yaxis_title="Impressions"), use_container_width=True)

        with st.expander("💡 Instructions de Téléchargement et Informations", expanded=False):
            st.markdown("""
            **Pour télécharger un graphique :**
            1. Survolez le graphique souhaité.
            2. Cliquez sur l'icône **appareil photo 📷** qui apparaît en haut à droite.
            3. L'image sera téléchargée au format PNG haute résolution.

            Les noms des fichiers sont générés automatiquement pour une organisation facile.
            """)

    else:
        st.info("Veuillez charger un fichier pour démarrer l'analyse.")

if __name__ == "__main__":
    main()
