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

# --- Fonctions de Gestion de Session ---
def get_colors():
    if 'custom_colors' not in st.session_state:
        st.session_state.custom_colors = DEFAULT_COLORS.copy()
    return st.session_state.custom_colors

def get_style_options():
    if 'style_options' not st.session_state:
        st.session_state.style_options = DEFAULT_STYLE_OPTIONS.copy()
    return st.session_state.style_options

# --- Fonctions Utilitaires et de Traitement de Données ---
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df['start_date'] = pd.to_datetime(df['start_date']).dt.date
    return df

def is_marque_query(query, regex_pattern):
    if pd.isna(query) or not regex_pattern: return False
    try: return bool(re.search(regex_pattern, str(query), re.IGNORECASE))
    except re.error: return False

def get_start_of_month(d, months_to_subtract=0):
    year, month = d.year, d.month
    month -= months_to_subtract
    while month <= 0:
        month += 12
        year -= 1
    return datetime(year, month, 1).date()

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

# ... (Les fonctions de création de graphiques et UI de personnalisation restent les mêmes) ...
# (Le code est omis ici pour la clarté mais doit être présent dans votre fichier)
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
        # ... (code for customization UI)
        pass

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
        df = load_data(uploaded_file)
        st.success(f"✅ Fichier chargé avec {len(df):,} lignes.")
        
        # Date d'ancrage: dernier jour du mois précédent
        today = datetime.now().date()
        anchor_date = today.replace(day=1) - timedelta(days=1)
        st.info(f"💡 L'analyse se base sur les mois entièrement terminés. La date de référence est le **{anchor_date.strftime('%d/%m/%Y')}**.")

        st.markdown("### 📅 Type de Comparaison")
        comparison_mode = st.radio(
            "Choisissez comment comparer les périodes :",
            ["Périodes Consécutives (ex: Q2 vs Q1)", "Année sur Année (YoY, ex: Q2 2024 vs Q2 2023)"],
            horizontal=True,
            help="**Consécutives**: Compare une période avec celle qui la précède. **YoY**: Compare une période avec la même période de l'année précédente."
        )

        periode_n_dates = None
        
        if comparison_mode == "Périodes Consécutives (ex: Q2 vs Q1)":
            options = {
                "3 derniers mois complets": {"name": "3 derniers mois", "months": 3},
                "6 derniers mois complets": {"name": "6 derniers mois", "months": 6},
                "Dernier mois complet": {"name": "Dernier mois", "months": 1},
                "Dernier trimestre complet": {"name": "Dernier trimestre", "months": 3, "quarter": True},
            }
            selection = st.radio("Choisissez une période :", options.keys(), horizontal=True)
            
            config = options[selection]
            n_end = anchor_date
            n_start = get_start_of_month(anchor_date, config["months"] - 1)
            n1_end = n_start - timedelta(days=1)
            n1_start = get_start_of_month(n1_end, config["months"] - 1)
            
            periode_n_dates, periode_n1_dates = (n_start, n_end), (n1_start, n1_end)
            period_type = f"{config['name']} vs Précédent"

        else: # Année sur Année (YoY)
            options_yoy = ["3 derniers mois complets", "Sélection Personnalisée"]
            selection_yoy = st.radio("Choisissez une période (comparaison YoY) :", options_yoy, horizontal=True)

            if selection_yoy == "3 derniers mois complets":
                n_end = anchor_date
                n_start = get_start_of_month(anchor_date, 2)
                
                n1_start = n_start.replace(year=n_start.year - 1)
                n1_end = n_end.replace(year=n_end.year - 1)
                
                periode_n_dates, periode_n1_dates = (n_start, n_end), (n1_start, n1_end)
                period_type = "3 derniers mois vs N-1 (YoY)"

            else: # Sélection Personnalisée YoY
                with st.expander("📅 Définir une période personnalisée (YoY)", expanded=True):
                    available_years = sorted(pd.to_datetime(df['start_date']).dt.year.unique(), reverse=True)
                    month_names = {i: calendar.month_name[i] for i in range(1, 13)}

                    st.markdown("**Période N (actuelle)**")
                    col1, col2 = st.columns(2)
                    start_month = col1.selectbox("Mois de début", month_names.keys(), format_func=lambda m: month_names[m], index=0)
                    start_year = col2.selectbox("Année de début", available_years, index=0)

                    st.markdown("")
                    col3, col4 = st.columns(2)
                    end_month = col3.selectbox("Mois de fin", month_names.keys(), format_func=lambda m: month_names[m], index=anchor_date.month - 2 if anchor_date.month > 1 else 11)
                    end_year = col4.selectbox("Année de fin", available_years, index=0)

                    try:
                        n_start = datetime(start_year, start_month, 1).date()
                        last_day_of_month = calendar.monthrange(end_year, end_month)[1]
                        n_end = datetime(end_year, end_month, last_day_of_month).date()

                        if n_start > n_end:
                            st.error("La date de début ne peut pas être après la date de fin.")
                        else:
                            n1_start = n_start.replace(year=n_start.year - 1)
                            n1_end = n_end.replace(year=n_end.year - 1)
                            periode_n_dates, periode_n1_dates = (n_start, n_end), (n1_start, n1_end)
                            period_type = "Période Personnalisée (YoY)"
                    except Exception as e:
                        st.error(f"Erreur dans la sélection des dates : {e}")

        if periode_n_dates:
            st.markdown("---")
            st.markdown("### 🔎 Périodes Sélectionnées pour l'Analyse")
            st.write(f"**Période N (actuelle) :** `{periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')}`")
            st.write(f"**Période N-1 (comparaison) :** `{periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}`")
            
            metrics = process_data_for_periods(df, periode_n_dates, periode_n1_dates, regex_pattern)
            
            if metrics['total_clics_n'] == 0 and metrics['total_clics_n1'] == 0:
                st.warning("⚠️ Aucune donnée trouvée pour les périodes sélectionnées.")
            else:
                st.markdown("---")
                st.markdown("### 📈 Résumé et Graphiques")
                
                chart_configs = {
                    "global": {"title": "Trafic SEO Global", "yaxis_title": "Clics", "metric_n": "total_clics_n", "metric_n1": "total_clics_n1", "color": get_colors()['global_seo']},
                    "marque": {"title": "Trafic SEO Marque", "yaxis_title": "Clics", "metric_n": "clics_marque_n", "metric_n1": "clics_marque_n1", "color": get_colors()['marque_clics']},
                    "hors_marque": {"title": "Trafic SEO Hors-Marque", "yaxis_title": "Clics", "metric_n": "clics_hors_marque_n", "metric_n1": "clics_hors_marque_n1", "color": get_colors()['hors_marque']},
                    "impressions": {"title": "Impressions SEO Marque", "yaxis_title": "Impressions", "metric_n": "impressions_marque_n", "metric_n1": "impressions_marque_n1", "color": get_colors()['impressions_marque']}
                }
                
                st.plotly_chart(create_evolution_chart(metrics, period_type, get_style_options()), use_container_width=True)
                pie1, pie2 = create_pie_charts(metrics, get_style_options())
                col1, col2 = st.columns(2)
                col1.plotly_chart(pie1, use_container_width=True)
                col2.plotly_chart(pie2, use_container_width=True)
                
                for config in chart_configs.values():
                    st.plotly_chart(create_generic_bar_chart(metrics, period_type, get_style_options(), config), use_container_width=True)

if __name__ == "__main__":
    main()
