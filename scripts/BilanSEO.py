import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
import calendar # Ajout de cet import

# --- Configuration de la Page ---
st.set_page_config(
    page_title="Dashboard SEO - Générateur de Graphiques",
    page_icon="📊",
    layout="wide"
)

# --- Couleurs et Styles par Défaut ---
DEFAULT_COLORS = {
    'global_seo': '#2563EB',
    'marque_clics': '#1E40AF',
    'impressions_marque': '#3730A3',
    'hors_marque': '#2563EB',
    'pie_marque': '#1E40AF',
    'pie_hors_marque': '#A5B4FC',
    'evolution_positive': '#10B981',
    'evolution_negative': '#EF4444',
    'secondary_light': '#A5B4FC',
    'secondary_dark': '#2563EB'
}

DEFAULT_STYLE_OPTIONS = {
    'font_family': 'Arial',
    'title_font_size': 18,
    'axis_font_size': 12,
    'bar_text_font_size': 12
}

# --- Fonctions de Gestion de Session (Couleurs & Styles) ---

def get_colors():
    """Récupère les couleurs depuis la session ou utilise les couleurs par défaut"""
    if 'custom_colors' not in st.session_state:
        st.session_state.custom_colors = DEFAULT_COLORS.copy()
    return st.session_state.custom_colors

def get_style_options():
    """Récupère les options de style depuis la session ou utilise les options par défaut"""
    if 'style_options' not in st.session_state:
        st.session_state.style_options = DEFAULT_STYLE_OPTIONS.copy()
    return st.session_state.style_options

# --- Fonctions Utilitaires et de Traitement de Données (avec Caching) ---

@st.cache_data
def load_data(uploaded_file):
    """Charge et prépare le fichier Excel. Mis en cache pour la performance."""
    df = pd.read_excel(uploaded_file)
    df['start_date'] = pd.to_datetime(df['start_date']).dt.date
    return df

@st.cache_data
def filter_incomplete_months(_df):
    """Filtre le DataFrame pour ne garder que les mois avec des données complètes."""
    df = _df.copy()
    df['year'] = pd.to_datetime(df['start_date']).dt.year
    df['month'] = pd.to_datetime(df['start_date']).dt.month
    
    # Calcule les jours attendus vs jours présents pour chaque mois/année
    monthly_days = df.groupby(['year', 'month'])['start_date'].nunique().reset_index()
    monthly_days.rename(columns={'start_date': 'days_present'}, inplace=True)
    
    # Fonction pour obtenir le nombre de jours dans un mois
    def get_days_in_month(row):
        return calendar.monthrange(row['year'], row['month'])[1]
        
    monthly_days['days_expected'] = monthly_days.apply(get_days_in_month, axis=1)
    
    # Identifie les mois complets
    complete_months = monthly_days[monthly_days['days_present'] == monthly_days['days_expected']]
    
    # Garde uniquement les données des mois complets
    df_filtered = df.merge(complete_months[['year', 'month']], on=['year', 'month'], how='inner')
    
    return df_filtered.drop(columns=['year', 'month'])

def is_marque_query(query, regex_pattern):
    """Identifie les requêtes de marque avec la regex personnalisée"""
    if pd.isna(query) or not regex_pattern:
        return False
    try:
        return bool(re.search(regex_pattern, str(query), re.IGNORECASE))
    except re.error:
        return False

@st.cache_data
def process_data_for_periods(_df, periode_n_dates, periode_n1_dates, regex_pattern):
    """Traite les données pour les périodes données. Mis en cache."""
    df = _df.copy()
    df['is_marque'] = df['query'].apply(lambda x: is_marque_query(x, regex_pattern))
    
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
        'nom_periode_n1': f"{periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}",
        'nom_periode_n': f"{periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')}"
    }
    return metrics

@st.cache_data
def process_monthly_data(_df, year_n, year_n1, regex_pattern):
    """Traite les données pour une comparaison mois par mois. Mis en cache."""
    df = _df.copy()
    df['month'] = pd.to_datetime(df['start_date']).dt.month
    df['year'] = pd.to_datetime(df['start_date']).dt.year
    df['is_marque'] = df['query'].apply(lambda x: is_marque_query(x, regex_pattern))
    
    data_n = df[df['year'] == year_n]
    data_n1 = df[df['year'] == year_n1]
    
    months_n = set(data_n['month'].unique()) if len(data_n) > 0 else set()
    months_n1 = set(data_n1['month'].unique()) if len(data_n1) > 0 else set()
    comparable_months = sorted(months_n.intersection(months_n1))
    
    if not comparable_months:
        return None
        
    month_names = {1: 'Jan', 2: 'Fév', 3: 'Mar', 4: 'Avr', 5: 'Mai', 6: 'Juin', 7: 'Juil', 8: 'Août', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Déc'}
    
    monthly_data = {
        'months': [month_names[m] for m in comparable_months], 'month_numbers': comparable_months,
        'year_n': year_n, 'year_n1': year_n1, 'months_count': len(comparable_months),
        'total_clics_n': [], 'total_clics_n1': [], 'clics_marque_n': [], 'clics_marque_n1': [],
        'clics_hors_marque_n': [], 'clics_hors_marque_n1': [], 'impressions_marque_n': [],
        'impressions_marque_n1': [], 'total_impressions_n': [], 'total_impressions_n1': []
    }
    
    for month_num in comparable_months:
        month_data_n = data_n[data_n['month'] == month_num]
        monthly_data['total_clics_n'].append(month_data_n['clicks'].sum())
        monthly_data['clics_marque_n'].append(month_data_n[month_data_n['is_marque']]['clicks'].sum())
        monthly_data['clics_hors_marque_n'].append(month_data_n[~month_data_n['is_marque']]['clicks'].sum())
        monthly_data['impressions_marque_n'].append(month_data_n[month_data_n['is_marque']]['impressions'].sum())
        monthly_data['total_impressions_n'].append(month_data_n['impressions'].sum())
        
        month_data_n1 = data_n1[data_n1['month'] == month_num]
        monthly_data['total_clics_n1'].append(month_data_n1['clicks'].sum())
        monthly_data['clics_marque_n1'].append(month_data_n1[month_data_n1['is_marque']]['clicks'].sum())
        monthly_data['clics_hors_marque_n1'].append(month_data_n1[~month_data_n1['is_marque']]['clicks'].sum())
        monthly_data['impressions_marque_n1'].append(month_data_n1[month_data_n1['is_marque']]['impressions'].sum())
        monthly_data['total_impressions_n1'].append(month_data_n1['impressions'].sum())
        
    return monthly_data

# --- Fonctions de Génération de Graphiques (Refactorisées et avec options de style) ---

def create_evolution_chart(metrics, period_type, style_options):
    """Graphique de synthèse des évolutions - N vs N-1"""
    COLORS = get_colors()
    evolutions = []
    
    if metrics['total_clics_n1'] > 0: evolutions.append({'Métrique': 'Total Clics', 'Évolution': ((metrics['total_clics_n'] - metrics['total_clics_n1']) / metrics['total_clics_n1'] * 100)})
    if metrics['clics_marque_n1'] > 0: evolutions.append({'Métrique': 'Clics Marque', 'Évolution': ((metrics['clics_marque_n'] - metrics['clics_marque_n1']) / metrics['clics_marque_n1'] * 100)})
    if metrics['clics_hors_marque_n1'] > 0: evolutions.append({'Métrique': 'Clics Hors-Marque', 'Évolution': ((metrics['clics_hors_marque_n'] - metrics['clics_hors_marque_n1']) / metrics['clics_hors_marque_n1'] * 100)})
    if metrics['impressions_marque_n1'] > 0: evolutions.append({'Métrique': 'Impressions Marque', 'Évolution': ((metrics['impressions_marque_n'] - metrics['impressions_marque_n1']) / metrics['impressions_marque_n1'] * 100)})
    if metrics['total_impressions_n1'] > 0: evolutions.append({'Métrique': 'Total Impressions', 'Évolution': ((metrics['total_impressions_n'] - metrics['total_impressions_n1']) / metrics['total_impressions_n1'] * 100)})
    
    if not evolutions: return None
    
    df_evo = pd.DataFrame(evolutions)
    colors = [COLORS['evolution_positive'] if x >= 0 else COLORS['evolution_negative'] for x in df_evo['Évolution']]
    
    fig = go.Figure(data=[go.Bar(
        x=df_evo['Métrique'], y=df_evo['Évolution'], marker_color=colors,
        text=[f"{x:+.1f}%" for x in df_evo['Évolution']], textposition='auto',
        textfont=dict(size=style_options['bar_text_font_size'], color='white')
    )])
    
    fig.update_layout(
        title=f"Synthèse des Évolutions (%) - {period_type}",
        font=dict(family=style_options['font_family'], size=style_options['axis_font_size'], color='black'),
        title_font_size=style_options['title_font_size'],
        height=500, plot_bgcolor='white', yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black')
    )
    return fig

def create_pie_charts(metrics, period_type, style_options):
    """Camemberts Marque/Hors-Marque"""
    COLORS = get_colors()
    figs = []
    
    for period in ['n1', 'n']:
        total_clicks = metrics[f'clics_marque_{period}'] + metrics[f'clics_hors_marque_{period}']
        if total_clicks > 0:
            pct_marque = (metrics[f'clics_marque_{period}'] / total_clicks * 100)
            pct_hors_marque = (metrics[f'clics_hors_marque_{period}'] / total_clicks * 100)
            
            labels = [f'Hors-Marque<br>{metrics[f"clics_hors_marque_{period}"]:,} ({pct_hors_marque:.1f}%)', 
                      f'Marque<br>{metrics[f"clics_marque_{period}"]:,} ({pct_marque:.1f}%)']
            values = [metrics[f'clics_hors_marque_{period}'], metrics[f'clics_marque_{period}']]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels, values=values,
                marker_colors=[COLORS['pie_hors_marque'], COLORS['pie_marque']],
                hole=0.4, textinfo='label', textposition='auto',
                textfont=dict(size=style_options['axis_font_size'])
            )])
            
            title_suffix = "N-1" if period == 'n1' else "N"
            fig.update_layout(
                title=f"Répartition {title_suffix}: {metrics[f'nom_periode_{period}']}",
                height=450,
                font=dict(family=style_options['font_family'], size=10, color='black'),
                title_font_size=style_options['title_font_size']
            )
            figs.append(fig)
        else:
            figs.append(go.Figure().update_layout(title=f"Pas de données pour la période {period.upper()}", height=450))

    return figs[0], figs[1]

def create_generic_bar_chart(metrics, period_type, style_options, config):
    """Crée un graphique en barres générique pour la comparaison par blocs."""
    fig = go.Figure(data=[go.Bar(
        x=[f"Période N-1<br>{metrics['nom_periode_n1']}", f"Période N<br>{metrics['nom_periode_n']}"],
        y=[metrics[config['metric_n1']], metrics[config['metric_n']]],
        marker_color=config['color'],
        text=[f"{metrics[config['metric_n1']]:,}", f"{metrics[config['metric_n']]:,}"],
        textposition='auto',
        textfont=dict(size=style_options['bar_text_font_size'], color='white')
    )])
    
    fig.update_layout(
        title=f"{config['title']} ({config['yaxis_title']}) - {period_type}",
        xaxis_title="Période", yaxis_title=config['yaxis_title'],
        font=dict(family=style_options['font_family'], size=style_options['axis_font_size'], color='black'),
        title_font_size=style_options['title_font_size'],
        height=500, showlegend=False, plot_bgcolor='white'
    )
    return fig

def create_generic_monthly_bar_chart(monthly_data, style_options, config):
    """Crée un graphique en barres mensuel générique."""
    COLORS = get_colors()
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=monthly_data['months'], y=monthly_data[config['metric_n1']], name=f'{monthly_data["year_n1"]}',
        marker_color=COLORS['secondary_light'],
        text=[f"{x:,}" if x > 0 else "" for x in monthly_data[config['metric_n1']]],
        textposition='auto', textfont=dict(size=style_options['bar_text_font_size'])
    ))
    
    fig.add_trace(go.Bar(
        x=monthly_data['months'], y=monthly_data[config['metric_n']], name=f'{monthly_data["year_n"]}',
        marker_color=config['color'],
        text=[f"{x:,}" if x > 0 else "" for x in monthly_data[config['metric_n']]],
        textposition='auto', textfont=dict(size=style_options['bar_text_font_size'])
    ))
    
    fig.update_layout(
        title=f"{config['title']} par Mois - {monthly_data['year_n1']} vs {monthly_data['year_n']}",
        xaxis_title="Mois", yaxis_title=config['yaxis_title'], barmode='group',
        font=dict(family=style_options['font_family'], size=style_options['axis_font_size'], color='black'),
        title_font_size=style_options['title_font_size'],
        height=500, plot_bgcolor='white'
    )
    return fig

# --- Fonctions UI ---

def show_chart_customization():
    """Interface pour personnaliser les couleurs et les polices."""
    st.markdown("### 🎨 Personnalisation des Graphiques")
    
    with st.expander("Modifier les couleurs, polices et tailles", expanded=False):
        COLORS = get_colors()
        STYLES = get_style_options()
        
        tab1, tab2 = st.tabs(["Couleurs", "Polices & Tailles"])
        
        with tab1:
            st.markdown("**Couleurs des graphiques**")
            col1, col2 = st.columns(2)
            with col1:
                COLORS['global_seo'] = st.color_picker("Trafic SEO Global", COLORS['global_seo'])
                COLORS['marque_clics'] = st.color_picker("Trafic Marque", COLORS['marque_clics'])
                COLORS['hors_marque'] = st.color_picker("Trafic Hors-Marque", COLORS['hors_marque'])
                COLORS['impressions_marque'] = st.color_picker("Impressions Marque", COLORS['impressions_marque'])
            with col2:
                COLORS['pie_marque'] = st.color_picker("Camembert - Marque", COLORS['pie_marque'])
                COLORS['pie_hors_marque'] = st.color_picker("Camembert - Hors-Marque", COLORS['pie_hors_marque'])
                COLORS['evolution_positive'] = st.color_picker("Évolution Positive", COLORS['evolution_positive'])
                COLORS['evolution_negative'] = st.color_picker("Évolution Négative", COLORS['evolution_negative'])
        
        with tab2:
            st.markdown("**Police des graphiques**")
            STYLES['font_family'] = st.selectbox(
                "Famille de police",
                ['Arial', 'Verdana', 'Helvetica', 'Garamond', 'Times New Roman', 'Courier New'],
                index=['Arial', 'Verdana', 'Helvetica', 'Garamond', 'Times New Roman', 'Courier New'].index(STYLES['font_family'])
            )
            
            st.markdown("**Tailles des textes (en pixels)**")
            STYLES['title_font_size'] = st.slider("Taille du titre", 10, 30, STYLES['title_font_size'])
            STYLES['axis_font_size'] = st.slider("Taille des axes", 8, 20, STYLES['axis_font_size'])
            STYLES['bar_text_font_size'] = st.slider("Taille du texte sur les barres", 8, 20, STYLES['bar_text_font_size'])

        st.session_state.custom_colors = COLORS
        st.session_state.style_options = STYLES
        
        if st.button("🔄 Réinitialiser les styles et couleurs"):
            st.session_state.custom_colors = DEFAULT_COLORS.copy()
            st.session_state.style_options = DEFAULT_STYLE_OPTIONS.copy()
            st.rerun()

def get_predefined_periods():
    today = datetime.now().date()
    return {
        "7_derniers_jours": {"name": "7 derniers jours", "periode_n": (today - timedelta(days=6), today), "periode_n1": (today - timedelta(days=13), today - timedelta(days=7))},
        "28_derniers_jours": {"name": "28 derniers jours", "periode_n": (today - timedelta(days=27), today), "periode_n1": (today - timedelta(days=55), today - timedelta(days=28))},
        "3_derniers_mois": {"name": "3 derniers mois", "periode_n": (today - timedelta(days=89), today), "periode_n1": (today - timedelta(days=179), today - timedelta(days=90))},
        "6_derniers_mois": {"name": "6 derniers mois", "periode_n": (today - timedelta(days=179), today), "periode_n1": (today - timedelta(days=359), today - timedelta(days=180))}
    }

# --- Application Principale ---

def main():
    st.title("📊 Dashboard SEO - Générateur de Graphiques")
    st.markdown("**Analysez vos performances SEO sur différentes périodes avec des visualisations personnalisées.**")
    
    show_chart_customization()
    
    st.markdown("---")
    st.markdown("### 🏷️ Configuration de la Marque")
    regex_pattern = st.text_input("Regex pour identifier les requêtes de marque", value="weefin|wee fin", help="Exemple: 'monsite|mon site|MonSite'")
    
    try: re.compile(regex_pattern)
    except re.error:
        st.error("❌ Regex invalide - Veuillez corriger")
        st.stop()
        
    st.markdown("---")
    uploaded_file = st.file_uploader("Uploadez votre fichier Google Search Console (Excel)", type=['xlsx', 'xls'])
    
    if uploaded_file:
        try:
            df = load_data(uploaded_file)
            st.success(f"✅ Fichier chargé avec {len(df):,} lignes.")
            
            COLORS = get_colors()
            STYLES = get_style_options()

            analysis_type = st.radio(
                "Choisissez le type de comparaison :",
                ["Comparaison par Blocs/Périodes", "Comparaison Mensuelle (Année N vs N-1)"],
                horizontal=True
            )
            
            st.markdown("---")
            st.markdown("### 📅 Sélection des Périodes")
            
            if analysis_type == "Comparaison par Blocs/Périodes":
                period_options = ["3 derniers mois", "6 derniers mois", "28 derniers jours", "7 derniers jours", "Personnalisée"]
                selected_period_key = st.radio("Choisissez une période d'analyse:", period_options, index=0, horizontal=True)
                
                if selected_period_key == "Personnalisée":
                    max_date = df['start_date'].max()
                    default_start_n = max_date - timedelta(days=89)
                    col1, col2 = st.columns(2)
                    start_n = col1.date_input("Date de début N", value=default_start_n)
                    end_n = col2.date_input("Date de fin N", value=max_date)
                    start_n1 = col1.date_input("Date de début N-1")
                    end_n1 = col2.date_input("Date de fin N-1")
                    periode_n_dates, periode_n1_dates = (start_n, end_n), (start_n1, end_n1)
                    period_type = "Période Personnalisée"
                else:
                    predefined = get_predefined_periods()
                    key_map = {"7 derniers jours": "7_derniers_jours", "28 derniers jours": "28_derniers_jours", "3 derniers mois": "3_derniers_mois", "6 derniers mois": "6_derniers_mois"}
                    key = key_map[selected_period_key]
                    periode_n_dates, periode_n1_dates = predefined[key]["periode_n"], predefined[key]["periode_n1"]
                    period_type = predefined[key]["name"]
                    st.info(f"**Période N**: {periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')} | **Période N-1**: {periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}")

                metrics = process_data_for_periods(df, periode_n_dates, periode_n1_dates, regex_pattern)
                
                if metrics['total_clics_n'] == 0 and metrics['total_clics_n1'] == 0:
                    st.warning("⚠️ Aucune donnée trouvée pour les périodes sélectionnées.")
                    st.stop()
                    
                st.markdown("---")
                st.markdown("### 📈 Résumé et Graphiques")
                
                # ... (affichage des métriques, évolutions, etc.) ...
                
                # Chart configurations
                chart_configs = {
                    "global": {"title": "Trafic SEO Global", "yaxis_title": "Clics", "metric_n": "total_clics_n", "metric_n1": "total_clics_n1", "color": COLORS['global_seo']},
                    "marque": {"title": "Trafic SEO Marque", "yaxis_title": "Clics", "metric_n": "clics_marque_n", "metric_n1": "clics_marque_n1", "color": COLORS['marque_clics']},
                    "hors_marque": {"title": "Trafic SEO Hors-Marque", "yaxis_title": "Clics", "metric_n": "clics_hors_marque_n", "metric_n1": "clics_hors_marque_n1", "color": COLORS['hors_marque']},
                    "impressions": {"title": "Impressions SEO Marque", "yaxis_title": "Impressions", "metric_n": "impressions_marque_n", "metric_n1": "impressions_marque_n1", "color": COLORS['impressions_marque']}
                }

                # Affichage des graphiques
                st.plotly_chart(create_evolution_chart(metrics, period_type, STYLES), use_container_width=True)
                
                pie1, pie2 = create_pie_charts(metrics, period_type, STYLES)
                col1, col2 = st.columns(2)
                col1.plotly_chart(pie1, use_container_width=True)
                col2.plotly_chart(pie2, use_container_width=True)
                
                for key, config in chart_configs.items():
                    st.plotly_chart(create_generic_bar_chart(metrics, period_type, STYLES, config), use_container_width=True)
            
            else: # Comparaison Mensuelle
                exclude_incomplete = st.checkbox("Exclure les mois incomplets (recommandé)", value=True, help="Ne compare que les mois pour lesquels les données de tous les jours sont disponibles dans le fichier.")
                
                df_monthly = df
                if exclude_incomplete:
                    df_filtered = filter_incomplete_months(df)
                    rows_removed = len(df) - len(df_filtered)
                    if rows_removed > 0:
                        st.info(f"ℹ️ {rows_removed:,} lignes de données ont été exclues car elles appartiennent à des mois incomplets.")
                    df_monthly = df_filtered
                
                current_year = datetime.now().year
                all_years = sorted(pd.to_datetime(df_monthly['start_date']).dt.year.unique(), reverse=True)
                selected_year = st.selectbox("Choisissez l'année N (actuelle) :", all_years, index=0)
                previous_year = selected_year - 1
                
                st.info(f"Comparaison de chaque mois de **{selected_year}** avec le même mois de **{previous_year}**.")
                
                metrics = process_monthly_data(df_monthly, selected_year, previous_year, regex_pattern)

                if metrics is None or metrics['months_count'] == 0:
                    st.warning(f"⚠️ Aucune donnée ou aucun mois comparable trouvé entre {selected_year} et {previous_year}. Essayez de décocher l'option d'exclusion des mois incomplets ou vérifiez vos données.")
                    st.stop()
                
                st.success(f"✅ **{metrics['months_count']} mois comparables trouvés** : {', '.join(metrics['months'])}")
                
                # Chart configurations pour mensuel
                monthly_chart_configs = {
                    "global": {"title": "Trafic SEO Global", "yaxis_title": "Clics", "metric_n": "total_clics_n", "metric_n1": "total_clics_n1", "color": COLORS['secondary_dark']},
                    "marque": {"title": "Trafic SEO Marque", "yaxis_title": "Clics", "metric_n": "clics_marque_n", "metric_n1": "clics_marque_n1", "color": COLORS['marque_clics']},
                    "hors_marque": {"title": "Trafic SEO Hors-Marque", "yaxis_title": "Clics", "metric_n": "clics_hors_marque_n", "metric_n1": "clics_hors_marque_n1", "color": COLORS['hors_marque']},
                    "impressions": {"title": "Impressions SEO Marque", "yaxis_title": "Impressions", "metric_n": "impressions_marque_n", "metric_n1": "impressions_marque_n1", "color": COLORS['impressions_marque']}
                }
                
                for key, config in monthly_chart_configs.items():
                    st.plotly_chart(create_generic_monthly_bar_chart(metrics, STYLES, config), use_container_width=True)

        except Exception as e:
            st.error(f"Une erreur est survenue lors du traitement du fichier : {e}")
            st.exception(e)

if __name__ == "__main__":
    main()
