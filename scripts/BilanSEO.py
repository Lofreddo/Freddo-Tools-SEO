import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
import calendar

# --- Configuration de la Page ---
st.set_page_config(
    page_title="Dashboard SEO - Générateur de Graphiques",
    page_icon="📊",
    layout="wide"
)

# --- Couleurs et Styles par Défaut ---
DEFAULT_COLORS = {
    'global_seo': '#2563EB', 'marque_clics': '#1E40AF', 'impressions_marque': '#3730A3',
    'hors_marque': '#2563EB', 'pie_marque': '#1E40AF', 'pie_hors_marque': '#A5B4FC',
    'evolution_positive': '#10B981', 'evolution_negative': '#EF4444',
    'secondary_light': '#A5B4FC', 'secondary_dark': '#2563EB'
}
DEFAULT_STYLE_OPTIONS = {
    'font_family': 'Arial', 'title_font_size': 18, 'axis_font_size': 12, 'bar_text_font_size': 12
}

# --- Fonctions de Gestion de Session (Couleurs & Styles) ---
def get_colors():
    if 'custom_colors' not in st.session_state:
        st.session_state.custom_colors = DEFAULT_COLORS.copy()
    return st.session_state.custom_colors

def get_style_options():
    if 'style_options' not in st.session_state:
        st.session_state.style_options = DEFAULT_STYLE_OPTIONS.copy()
    return st.session_state.style_options

# --- Fonctions Utilitaires et de Traitement de Données (avec Caching) ---
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df['start_date'] = pd.to_datetime(df['start_date']).dt.date
    return df

def is_marque_query(query, regex_pattern):
    if pd.isna(query) or not regex_pattern: return False
    try: return bool(re.search(regex_pattern, str(query), re.IGNORECASE))
    except re.error: return False

def get_complete_month_periods(anchor_date):
    """Calcule des périodes de comparaison basées sur des mois complets."""
    periods = {}

    def get_start_of_month(d, months_to_subtract=0):
        year, month = d.year, d.month
        month -= months_to_subtract
        while month <= 0:
            month += 12
            year -= 1
        return datetime(year, month, 1).date()

    n_end = anchor_date
    
    # 1 mois
    n_start_1m = get_start_of_month(n_end, 0)
    n1_end_1m = n_start_1m - timedelta(days=1)
    n1_start_1m = get_start_of_month(n1_end_1m, 0)
    periods["dernier_mois_complet"] = {"name": "Dernier mois complet", "periode_n": (n_start_1m, n_end), "periode_n1": (n1_start_1m, n1_end_1m)}
    
    # 3 mois
    n_start_3m = get_start_of_month(n_end, 2)
    n1_end_3m = n_start_3m - timedelta(days=1)
    n1_start_3m = get_start_of_month(n1_end_3m, 2)
    periods["3_derniers_mois_complets"] = {"name": "3 derniers mois complets", "periode_n": (n_start_3m, n_end), "periode_n1": (n1_start_3m, n1_end_3m)}
    
    # 6 mois
    n_start_6m = get_start_of_month(n_end, 5)
    n1_end_6m = n_start_6m - timedelta(days=1)
    n1_start_6m = get_start_of_month(n1_end_6m, 5)
    periods["6_derniers_mois_complets"] = {"name": "6 derniers mois complets", "periode_n": (n_start_6m, n_end), "periode_n1": (n1_start_6m, n1_end_6m)}

    # 12 mois
    n_start_12m = get_start_of_month(n_end, 11)
    n1_end_12m = n_start_12m - timedelta(days=1)
    n1_start_12m = get_start_of_month(n1_end_12m, 11)
    periods["12_derniers_mois_complets"] = {"name": "12 derniers mois complets", "periode_n": (n_start_12m, n_end), "periode_n1": (n1_start_12m, n1_end_12m)}
    
    # Dernier trimestre complet
    current_quarter = (anchor_date.month - 1) // 3
    q_end_year = anchor_date.year
    
    q_end_month = current_quarter * 3
    q_start_month = q_end_month - 2
    
    q_n_start = datetime(q_end_year, q_start_month, 1).date()
    q_n_end = (datetime(q_end_year, q_end_month, 1).replace(day=calendar.monthrange(q_end_year, q_end_month)[1])).date()
    
    q_n1_end = q_n_start - timedelta(days=1)
    q_n1_start = get_start_of_month(q_n1_end, 2)
    periods["dernier_trimestre_complet"] = {"name": "Dernier trimestre complet", "periode_n": (q_n_start, q_n_end), "periode_n1": (q_n1_start, q_n1_end)}

    return periods

@st.cache_data
def process_data_for_periods(_df, periode_n_dates, periode_n1_dates, regex_pattern):
    df = _df.copy()
    df['is_marque'] = df['query'].apply(lambda x: is_marque_query(x, regex_pattern))
    
    periode_n = df[(df['start_date'] >= periode_n_dates[0]) & (df['start_date'] <= periode_n_dates[1])]
    periode_n1 = df[(df['start_date'] >= periode_n1_dates[0]) & (df['start_date'] <= periode_n1_dates[1])]
    
    metrics = {
        'total_clics_n1': periode_n1['clicks'].sum(), 'total_clics_n': periode_n['clicks'].sum(),
        'clics_marque_n1': periode_n1[periode_n1['is_marque']]['clicks'].sum(), 'clics_marque_n': periode_n[periode_n['is_marque']]['clicks'].sum(),
        'clics_hors_marque_n1': periode_n1[~periode_n1['is_marque']]['clicks'].sum(), 'clics_hors_marque_n': periode_n[~periode_n['is_marque']]['clicks'].sum(),
        'impressions_marque_n1': periode_n1[periode_n1['is_marque']]['impressions'].sum(), 'impressions_marque_n': periode_n[periode_n['is_marque']]['impressions'].sum(),
        'total_impressions_n1': periode_n1['impressions'].sum(), 'total_impressions_n': periode_n['impressions'].sum(),
        'nom_periode_n1': f"{periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}",
        'nom_periode_n': f"{periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')}"
    }
    return metrics
    
# --- Fonctions de création de graphiques ---
def create_evolution_chart(metrics, period_type, style_options):
    COLORS, evolutions = get_colors(), []
    if metrics['total_clics_n1'] > 0: evolutions.append({'Métrique': 'Total Clics', 'Évolution': ((metrics['total_clics_n'] - metrics['total_clics_n1']) / metrics['total_clics_n1'] * 100)})
    if metrics['clics_marque_n1'] > 0: evolutions.append({'Métrique': 'Clics Marque', 'Évolution': ((metrics['clics_marque_n'] - metrics['clics_marque_n1']) / metrics['clics_marque_n1'] * 100)})
    if metrics['clics_hors_marque_n1'] > 0: evolutions.append({'Métrique': 'Clics Hors-Marque', 'Évolution': ((metrics['clics_hors_marque_n'] - metrics['clics_hors_marque_n1']) / metrics['clics_hors_marque_n1'] * 100)})
    if metrics['total_impressions_n1'] > 0: evolutions.append({'Métrique': 'Total Impressions', 'Évolution': ((metrics['total_impressions_n'] - metrics['total_impressions_n1']) / metrics['total_impressions_n1'] * 100)})
    if not evolutions: return None
    df_evo = pd.DataFrame(evolutions)
    colors = [COLORS['evolution_positive'] if x >= 0 else COLORS['evolution_negative'] for x in df_evo['Évolution']]
    fig = go.Figure(data=[go.Bar(x=df_evo['Métrique'], y=df_evo['Évolution'], marker_color=colors, text=[f"{x:+.1f}%" for x in df_evo['Évolution']], textposition='auto', textfont=dict(size=style_options['bar_text_font_size'], color='white'))])
    fig.update_layout(title=f"Synthèse des Évolutions (%) - {period_type}", font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, plot_bgcolor='white', yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black'))
    return fig

def create_pie_charts(metrics, style_options):
    COLORS, figs = get_colors(), []
    for period in ['n1', 'n']:
        total = metrics[f'clics_marque_{period}'] + metrics[f'clics_hors_marque_{period}']
        if total > 0:
            labels = [f"Hors-Marque<br>{metrics[f'clics_hors_marque_{period}']:,} ({metrics[f'clics_hors_marque_{period}']/total*100:.1f}%)", f"Marque<br>{metrics[f'clics_marque_{period}']:,} ({metrics[f'clics_marque_{period}']/total*100:.1f}%)"]
            values = [metrics[f'clics_hors_marque_{period}'], metrics[f'clics_marque_{period}']]
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=[COLORS['pie_hors_marque'], COLORS['pie_marque']], hole=0.4, textinfo='label', textfont=dict(size=style_options['axis_font_size']))])
            title_suffix = "Période N-1" if period == 'n1' else "Période N"
            fig.update_layout(title=f"Répartition {title_suffix}: {metrics[f'nom_periode_{period}']}", height=450, font=dict(family=style_options['font_family']), title_font_size=style_options['title_font_size'])
            figs.append(fig)
        else:
            figs.append(go.Figure().update_layout(title=f"Pas de données pour la période {period.upper()}", height=450))
    return figs[0], figs[1]

def create_generic_bar_chart(metrics, period_type, style_options, config):
    fig = go.Figure(data=[go.Bar(x=[f"Période N-1<br>{metrics['nom_periode_n1']}", f"Période N<br>{metrics['nom_periode_n']}"], y=[metrics[config['metric_n1']], metrics[config['metric_n']]], marker_color=config['color'], text=[f"{metrics[config['metric_n1']]:,}", f"{metrics[config['metric_n']]:,}"], textposition='auto', textfont=dict(size=style_options['bar_text_font_size'], color='white'))])
    fig.update_layout(title=f"{config['title']} ({config['yaxis_title']}) - {period_type}", xaxis_title="Période", yaxis_title=config['yaxis_title'], font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, showlegend=False, plot_bgcolor='white')
    return fig

def show_chart_customization():
    with st.expander("🎨 Personnalisation des Graphiques", expanded=False):
        COLORS, STYLES = get_colors(), get_style_options()
        # ... (code for customization UI)
        if st.button("🔄 Réinitialiser les styles"):
            st.session_state.custom_colors, st.session_state.style_options = DEFAULT_COLORS.copy(), DEFAULT_STYLE_OPTIONS.copy()
            st.rerun()

# --- Application Principale ---
def main():
    st.title("📊 Dashboard SEO - Générateur de Graphiques")
    st.markdown("**Analysez vos performances SEO en comparant des périodes de mois complets.**")
    
    show_chart_customization()
    
    st.markdown("---")
    st.markdown("### 🏷️ Configuration de la Marque")
    regex_pattern = st.text_input("Regex pour identifier les requêtes de marque", value="weefin|wee fin")
    try: re.compile(regex_pattern)
    except re.error:
        st.error("❌ Regex invalide.")
        st.stop()
        
    st.markdown("---")
    uploaded_file = st.file_uploader("Uploadez votre fichier Google Search Console (Excel)", type=['xlsx', 'xls'])
    
    if uploaded_file:
        try:
            df = load_data(uploaded_file)
            st.success(f"✅ Fichier chargé avec {len(df):,} lignes.")
            
            COLORS, STYLES = get_colors(), get_style_options()

            st.markdown("### 📅 Sélection de la Période d'Analyse")
            
            today = datetime.now().date()
            anchor_date = today.replace(day=1) - timedelta(days=1)
            st.info(f"💡 L'analyse se base sur les mois entièrement terminés. La date de référence est le **{anchor_date.strftime('%d/%m/%Y')}**.")
            
            predefined_periods = get_complete_month_periods(anchor_date)
            period_options_map = {
                "3_derniers_mois_complets": "3 derniers mois complets", "6_derniers_mois_complets": "6 derniers mois complets",
                "12_derniers_mois_complets": "12 derniers mois complets", "dernier_mois_complet": "Dernier mois complet",
                "dernier_trimestre_complet": "Dernier trimestre complet"
            }

            selected_period_key = st.radio(
                "Choisissez une période d'analyse :", list(period_options_map.keys()),
                format_func=lambda key: period_options_map[key], index=0, horizontal=True
            )
            
            selected_config = predefined_periods[selected_period_key]
            periode_n_dates, periode_n1_dates = selected_config["periode_n"], selected_config["periode_n1"]
            period_type = selected_config["name"]

            st.write(f"**Période N (actuelle) :** `{periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')}`")
            st.write(f"**Période N-1 (précédente) :** `{periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}`")

            metrics = process_data_for_periods(df, periode_n_dates, periode_n1_dates, regex_pattern)
            
            if metrics['total_clics_n'] == 0 and metrics['total_clics_n1'] == 0:
                st.warning("⚠️ Aucune donnée trouvée pour les périodes sélectionnées.")
                st.stop()
                
            st.markdown("---")
            st.markdown("### 📈 Résumé et Graphiques")
            
            chart_configs = {
                "global": {"title": "Trafic SEO Global", "yaxis_title": "Clics", "metric_n": "total_clics_n", "metric_n1": "total_clics_n1", "color": COLORS['global_seo']},
                "marque": {"title": "Trafic SEO Marque", "yaxis_title": "Clics", "metric_n": "clics_marque_n", "metric_n1": "clics_marque_n1", "color": COLORS['marque_clics']},
                # ... etc
            }
            
            st.plotly_chart(create_evolution_chart(metrics, period_type, STYLES), use_container_width=True)
            pie1, pie2 = create_pie_charts(metrics, STYLES)
            col1, col2 = st.columns(2)
            col1.plotly_chart(pie1, use_container_width=True)
            col2.plotly_chart(pie2, use_container_width=True)
            # ... (boucle pour les bar charts)

        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")
            st.exception(e)

if __name__ == "__main__":
    main()
