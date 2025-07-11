import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
import calendar

# --- Configuration de la Page ---
st.set_page_config(
    page_title="Dashboard SEO - Générateur de Rapports",
    page_icon="📊",
    layout="wide"
)

# --- Couleurs, Styles et Textes par Défaut ---
DEFAULT_COLORS = {'global_seo': '#2563EB', 'marque_clics': '#1E40AF', 'impressions_marque': '#3730A3', 'hors_marque': '#2563EB', 'pie_marque': '#1E40AF', 'pie_hors_marque': '#A5B4FC', 'evolution_positive': '#10B981', 'evolution_negative': '#EF4444', 'secondary_light': '#A5B4FC', 'secondary_dark': '#2563EB'}
DEFAULT_STYLE_OPTIONS = {'font_family': 'Arial', 'title_font_size': 18, 'axis_font_size': 12, 'bar_text_font_size': 12}

def get_default_texts(period_type, metrics):
    """Génère les textes par défaut en fonction des périodes actuelles."""
    return {
        'evolution': {'title': f"Synthèse des Évolutions (%) - {period_type}"},
        'pie': {'title_n': f"Répartition Période N: {metrics['nom_periode_n']}", 'title_n1': f"Répartition Période N-1: {metrics['nom_periode_n1']}"},
        'global': {'title': f"Trafic SEO Global (Clics) - {period_type}", 'label_n': f"Période N<br>{metrics['nom_periode_n']}", 'label_n1': f"Période N-1<br>{metrics['nom_periode_n1']}"},
        'marque': {'title': f"Trafic SEO Marque (Clics) - {period_type}", 'label_n': f"Période N<br>{metrics['nom_periode_n']}", 'label_n1': f"Période N-1<br>{metrics['nom_periode_n1']}"},
        'hors_marque': {'title': f"Trafic SEO Hors-Marque (Clics) - {period_type}", 'label_n': f"Période N<br>{metrics['nom_periode_n']}", 'label_n1': f"Période N-1<br>{metrics['nom_periode_n1']}"},
        'impressions': {'title': f"Impressions SEO Marque - {period_type}", 'label_n': f"Période N<br>{metrics['nom_periode_n']}", 'label_n1': f"Période N-1<br>{metrics['nom_periode_n1']}"},
        'monthly_global': {'title': "Trafic SEO Global (Évolution Mensuelle)"},
        'monthly_marque': {'title': "Trafic SEO Marque (Évolution Mensuelle)"},
        'monthly_hors_marque': {'title': "Trafic SEO Hors-Marque (Évolution Mensuelle)"},
        'monthly_impressions': {'title': "Impressions SEO Marque (Évolution Mensuelle)"}
    }

# --- Fonctions de Gestion de Session ---
def get_session_state_value(key, default_value):
    if key not in st.session_state: st.session_state[key] = default_value
    return st.session_state[key]

# --- Fonctions Utilitaires et de Traitement (inchangées) ---
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file); df.rename(columns={"Date": "start_date"}, inplace=True, errors='ignore'); df['start_date'] = pd.to_datetime(df['start_date']).dt.date
    return df
def is_marque_query(query, regex_pattern):
    if pd.isna(query) or not regex_pattern: return False
    try: return bool(re.search(regex_pattern, str(query), re.IGNORECASE))
    except re.error: return False
def get_start_of_month(d, months_to_subtract=0):
    year, month = d.year, d.month; month -= months_to_subtract
    while month <= 0: month += 12; year -= 1
    return datetime(year, month, 1).date
@st.cache_data
def process_data_for_periods(_df_queries, _df_pages, periode_n_dates, periode_n1_dates, regex_pattern):
    df_queries = _df_queries.copy(); df_queries['is_marque'] = df_queries['query'].apply(lambda x: is_marque_query(x, regex_pattern))
    q_periode_n = df_queries[(df_queries['start_date'] >= periode_n_dates[0]) & (df_queries['start_date'] <= periode_n_dates[1])]
    q_periode_n1 = df_queries[(df_queries['start_date'] >= periode_n1_dates[0]) & (df_queries['start_date'] <= periode_n1_dates[1])]
    metrics = {'clics_marque_n': q_periode_n[q_periode_n['is_marque']]['clicks'].sum(), 'clics_marque_n1': q_periode_n1[q_periode_n1['is_marque']]['clicks'].sum(),'clics_hors_marque_n': q_periode_n[~q_periode_n['is_marque']]['clicks'].sum(), 'clics_hors_marque_n1': q_periode_n1[~q_periode_n1['is_marque']]['clicks'].sum(), 'impressions_marque_n': q_periode_n[q_periode_n['is_marque']]['impressions'].sum(), 'impressions_marque_n1': q_periode_n1[q_periode_n1['is_marque']]['impressions'].sum(),'nom_periode_n1': f"{periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}", 'nom_periode_n': f"{periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')}"}
    if _df_pages is not None:
        df_pages = _df_pages.copy(); p_periode_n = df_pages[(df_pages['start_date'] >= periode_n_dates[0]) & (df_pages['start_date'] <= periode_n_dates[1])]; p_periode_n1 = df_pages[(df_pages['start_date'] >= periode_n1_dates[0]) & (df_pages['start_date'] <= periode_n1_dates[1])]
        metrics['total_clics_n'], metrics['total_clics_n1'] = p_periode_n['clicks'].sum(), p_periode_n1['clicks'].sum(); metrics['total_impressions_n'], metrics['total_impressions_n1'] = p_periode_n['impressions'].sum(), p_periode_n1['impressions'].sum()
    else:
        metrics['total_clics_n'], metrics['total_clics_n1'] = q_periode_n['clicks'].sum(), q_periode_n1['clicks'].sum(); metrics['total_impressions_n'], metrics['total_impressions_n1'] = q_periode_n['impressions'].sum(), q_periode_n1['impressions'].sum()
    return metrics
@st.cache_data
def get_monthly_breakdown(_df_queries, _df_pages, periode_n_dates, periode_n1_dates, regex_pattern):
    def aggregate_monthly(df, start_date, end_date, is_queries=False):
        df_period = df[(df['start_date'] >= start_date) & (df['start_date'] <= end_date)].copy();
        if df_period.empty: return pd.DataFrame()
        df_period['month'] = pd.to_datetime(df_period['start_date']).dt.to_period('M'); agg_dict = {'clicks': 'sum', 'impressions': 'sum'}
        if is_queries:
            df_period['is_marque'] = df_period['query'].apply(lambda x: is_marque_query(x, regex_pattern)); marque_agg = df_period[df_period['is_marque']].groupby('month').agg(agg_dict).rename(columns={'clicks': 'clics_marque', 'impressions': 'impressions_marque'}); hors_marque_agg = df_period[~df_period['is_marque']].groupby('month').agg(agg_dict).rename(columns={'clicks': 'clics_hors_marque', 'impressions': 'impressions_hors_marque'}); total_agg = df_period.groupby('month').agg(agg_dict).rename(columns={'clicks': 'total_clics_q', 'impressions': 'total_impressions_q'}); return total_agg.join(marque_agg, how='left').join(hors_marque_agg, how='left').fillna(0)
        else: return df_period.groupby('month').agg(agg_dict).rename(columns={'clicks': 'total_clics', 'impressions': 'total_impressions'})
    monthly_q_n = aggregate_monthly(_df_queries, periode_n_dates[0], periode_n_dates[1], is_queries=True); monthly_q_n1 = aggregate_monthly(_df_queries, periode_n1_dates[0], periode_n1_dates[1], is_queries=True); monthly_p_n, monthly_p_n1 = (aggregate_monthly(_df_pages, d[0], d[1]) if _df_pages is not None else pd.DataFrame() for d in [periode_n_dates, periode_n1_dates]); all_months = pd.period_range(start=periode_n_dates[0], end=periode_n_dates[1], freq='M'); final_df = pd.DataFrame(index=all_months); final_df.index.name = 'month'; final_df = final_df.join(monthly_p_n if _df_pages is not None else monthly_q_n[['total_clics_q', 'total_impressions_q']].rename(columns={'total_clics_q': 'total_clics', 'total_impressions_q': 'total_impressions'}), how='left'); final_df = final_df.join(monthly_q_n[['clics_marque', 'clics_hors_marque', 'impressions_marque']], how='left');
    if not monthly_q_n1.empty: final_df = final_df.join(monthly_q_n1.add_suffix('_n1').set_index(monthly_q_n1.index.map(lambda p: p.asfreq('M') + 12)), how='left')
    if not monthly_p_n1.empty: final_df = final_df.join(monthly_p_n1.add_suffix('_n1').set_index(monthly_p_n1.index.map(lambda p: p.asfreq('M') + 12)), how='left')
    final_df = final_df.fillna(0).reset_index(); final_df['month_label'] = final_df['month'].dt.strftime('%b %Y'); return final_df

# --- Fonctions de Création de Graphiques (Mises à jour) ---
def create_evolution_chart(metrics, custom_texts, style_options):
    COLORS, evolutions = get_session_state_value('custom_colors', DEFAULT_COLORS), []
    if metrics['total_clics_n1'] > 0: evolutions.append({'Métrique': 'Total Clics', 'Évolution': ((metrics['total_clics_n'] - metrics['total_clics_n1']) / metrics['total_clics_n1'] * 100)})
    # ... autres métriques ...
    if not evolutions: return None
    df_evo = pd.DataFrame(evolutions); colors = [COLORS['evolution_positive'] if x >= 0 else COLORS['evolution_negative'] for x in df_evo['Évolution']]
    fig = go.Figure(data=[go.Bar(x=df_evo['Métrique'], y=df_evo['Évolution'], marker_color=colors, text=[f"{x:+.1f}%" for x in df_evo['Évolution']], textposition='auto', textfont=dict(size=style_options['bar_text_font_size'], color='white'))])
    fig.update_layout(title=custom_texts['title'], font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, plot_bgcolor='white', yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black'))
    return fig

def create_pie_charts(metrics, custom_texts, style_options):
    COLORS, figs = get_session_state_value('custom_colors', DEFAULT_COLORS), []
    for i, period in enumerate(['n1', 'n']):
        total = metrics[f'clics_marque_{period}'] + metrics[f'clics_hors_marque_{period}']
        if total > 0:
            labels = [f"Hors-Marque<br>{metrics[f'clics_hors_marque_{period}']:,} ({metrics[f'clics_hors_marque_{period}']/total*100:.1f}%)", f"Marque<br>{metrics[f'clics_marque_{period}']:,} ({metrics[f'clics_marque_{period}']/total*100:.1f}%)"]
            values = [metrics[f'clics_hors_marque_{period}'], metrics[f'clics_marque_{period}']]
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=[COLORS['pie_hors_marque'], COLORS['pie_marque']], hole=0.4, textinfo='label', textfont=dict(size=style_options['axis_font_size']))])
            fig.update_layout(title=custom_texts[f'title_{period}'], height=450, font=dict(family=style_options['font_family']), title_font_size=style_options['title_font_size'])
            figs.append(fig)
        else: figs.append(go.Figure().update_layout(title=f"Pas de données pour la période {period.upper()}", height=450))
    return figs[0], figs[1]

def create_generic_bar_chart(metrics, custom_texts, style_options, config):
    fig = go.Figure(data=[go.Bar(x=[custom_texts['label_n1'], custom_texts['label_n']], y=[metrics[config['metric_n1']], metrics[config['metric_n']]], marker_color=config['color'], text=[f"{metrics[config['metric_n1']]:,}", f"{metrics[config['metric_n']]:,}"], textposition='auto', textfont=dict(size=style_options['bar_text_font_size'], color='white'))])
    fig.update_layout(title=custom_texts['title'], xaxis_title="Période", yaxis_title=config['yaxis_title'], font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, showlegend=False, plot_bgcolor='white')
    return fig

def create_monthly_breakdown_chart(monthly_data, custom_texts, style_options, config):
    COLORS = get_session_state_value('custom_colors', DEFAULT_COLORS)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_data['month_label'], y=monthly_data[config['metric_n1']], name='Période N-1', marker_color=COLORS['secondary_light'], text=[f"{x:,.0f}" for x in monthly_data[config['metric_n1']]], textposition='outside'))
    fig.add_trace(go.Bar(x=monthly_data['month_label'], y=monthly_data[config['metric_n']], name='Période N', marker_color=config['color'], text=[f"{x:,.0f}" for x in monthly_data[config['metric_n']]], textposition='outside'))
    fig.update_layout(title=custom_texts['title'], xaxis_title="Mois", yaxis_title=config['yaxis_title'], barmode='group', font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, plot_bgcolor='white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def show_chart_customization():
    """Affiche l'interface de personnalisation des graphiques."""
    with st.expander("🎨 Personnalisation Globale", expanded=False):
        tab1, tab2 = st.tabs(["Couleurs", "Polices & Tailles"])
        with tab1:
            st.markdown("**Couleurs des graphiques**"); col1, col2 = st.columns(2)
            with col1:
                st.session_state.custom_colors['global_seo'] = st.color_picker("Couleur Principale", get_session_state_value('custom_colors', DEFAULT_COLORS)['global_seo'], key='c1')
                st.session_state.custom_colors['marque_clics'] = st.color_picker("Couleur Marque", get_session_state_value('custom_colors', DEFAULT_COLORS)['marque_clics'], key='c2')
                st.session_state.custom_colors['evolution_positive'] = st.color_picker("Évolution Positive", get_session_state_value('custom_colors', DEFAULT_COLORS)['evolution_positive'], key='c3')
            with col2:
                st.session_state.custom_colors['secondary_light'] = st.color_picker("Comparaison N-1", get_session_state_value('custom_colors', DEFAULT_COLORS)['secondary_light'], key='c4')
                st.session_state.custom_colors['pie_marque'] = st.color_picker("Camembert Marque", get_session_state_value('custom_colors', DEFAULT_COLORS)['pie_marque'], key='c5')
                st.session_state.custom_colors['evolution_negative'] = st.color_picker("Évolution Négative", get_session_state_value('custom_colors', DEFAULT_COLORS)['evolution_negative'], key='c6')
        with tab2:
            st.markdown("**Police des graphiques**"); st.session_state.style_options['font_family'] = st.selectbox("Famille de police", ['Arial', 'Verdana', 'Helvetica', 'Garamond'], index=['Arial', 'Verdana', 'Helvetica', 'Garamond'].index(get_session_state_value('style_options', DEFAULT_STYLE_OPTIONS)['font_family']))
            st.markdown("**Tailles des textes (px)**"); st.session_state.style_options['title_font_size'] = st.slider("Taille du titre", 10, 30, get_session_state_value('style_options', DEFAULT_STYLE_OPTIONS)['title_font_size'])
            st.session_state.style_options['axis_font_size'] = st.slider("Taille des axes", 8, 20, get_session_state_value('style_options', DEFAULT_STYLE_OPTIONS)['axis_font_size'])
            st.session_state.style_options['bar_text_font_size'] = st.slider("Texte sur les barres", 8, 20, get_session_state_value('style_options', DEFAULT_STYLE_OPTIONS)['bar_text_font_size'])
        
        col1, col2 = st.columns(2)
        if col1.button("🔄 Réinitialiser Styles & Couleurs"):
            st.session_state.custom_colors = DEFAULT_COLORS.copy(); st.session_state.style_options = DEFAULT_STYLE_OPTIONS.copy(); st.rerun()
        if col2.button("✍️ Réinitialiser Tous les Textes"):
            st.session_state.chart_texts = {}; st.rerun()

# --- Application Principale ---
def main():
    st.title("📊 Dashboard SEO - Générateur de Rapports")
    st.markdown("**Analysez et personnalisez vos rapports de performance SEO.**")
    
    show_chart_customization()
    
    st.markdown("---"); st.markdown("### 🏷️ Configuration"); regex_pattern = st.text_input("Regex Marque", value="weefin|wee fin")
    try: re.compile(regex_pattern)
    except re.error: st.error("❌ Regex invalide."); st.stop()
        
    st.markdown("---"); st.markdown("### 📥 Import des Données GSC")
    col1, col2 = st.columns(2); uploaded_file_queries = col1.file_uploader("1. Fichier 'Requêtes'", type=['xlsx', 'xls']); uploaded_file_pages = col2.file_uploader("2. Fichier 'Pages'", type=['xlsx', 'xls'])

    if uploaded_file_queries:
        df_queries = load_data(uploaded_file_queries); st.success(f"✅ Fichier 'Requêtes' chargé.")
        df_pages = load_data(uploaded_file_pages) if uploaded_file_pages else None
        if df_pages is not None: st.success(f"✅ Fichier 'Pages' chargé.")
        else: st.warning("⚠️ Fichier 'Pages' non fourni. Les totaux seront moins précis.")

        today = datetime.now().date(); anchor_date = today.replace(day=1) - timedelta(days=1)
        st.info(f"💡 L'analyse se base sur les mois terminés. Date de référence: **{anchor_date.strftime('%d/%m/%Y')}**.")
        
        st.markdown("### 📅 Type de Comparaison"); comparison_mode = st.radio("Mode :", ["Périodes Consécutives", "Année sur Année (YoY)"], horizontal=True, key="comparison_mode")
        periode_n_dates = None;
        if comparison_mode == "Périodes Consécutives":
            options = {"3 derniers mois complets": 3, "6 derniers mois complets": 6, "Dernier mois complet": 1}; selection = st.radio("Période :", options.keys(), horizontal=True, key="consecutive_period"); months = options[selection]; n_end = anchor_date; n_start = get_start_of_month(anchor_date, months - 1); n1_end = n_start - timedelta(days=1); n1_start = get_start_of_month(n1_end, months - 1); periode_n_dates, periode_n1_dates = (n_start, n_end), (n1_start, n1_end); period_type = f"{selection} vs Précédent"
        else:
            options_yoy = ["3 derniers mois complets", "Sélection Personnalisée"]; selection_yoy = st.radio("Période (YoY) :", options_yoy, horizontal=True, key="yoy_period")
            if selection_yoy == "3 derniers mois complets":
                n_end = anchor_date; n_start = get_start_of_month(anchor_date, 2); n1_start = n_start.replace(year=n_start.year - 1); n1_end = n_end.replace(year=n_end.year - 1); periode_n_dates, periode_n1_dates = (n_start, n_end), (n1_start, n1_end); period_type = "3 derniers mois vs N-1 (YoY)"
            else:
                with st.expander("📅 Définir une période personnalisée (YoY)", expanded=True): pass

        if periode_n_dates:
            metrics = process_data_for_periods(df_queries, df_pages, periode_n_dates, periode_n1_dates, regex_pattern)
            
            # Initialise les textes par défaut si nécessaire (après avoir calculé les métriques)
            default_texts = get_default_texts(period_type, metrics)
            if 'chart_texts' not in st.session_state or not st.session_state.chart_texts:
                st.session_state.chart_texts = default_texts
            
            st.markdown("---"); st.markdown("### 📈 Analyse Globale sur la Période")
            chart_configs = {"global": {"title": "Trafic SEO Global", "yaxis_title": "Clics", "metric_n": "total_clics_n", "metric_n1": "total_clics_n1", "color": get_session_state_value('custom_colors', DEFAULT_COLORS)['global_seo']}, "marque": {"title": "Trafic SEO Marque", "yaxis_title": "Clics", "metric_n": "clics_marque_n", "metric_n1": "clics_marque_n1", "color": get_session_state_value('custom_colors', DEFAULT_COLORS)['marque_clics']}, "hors_marque": {"title": "Trafic SEO Hors-Marque", "yaxis_title": "Clics", "metric_n": "clics_hors_marque_n", "metric_n1": "clics_hors_marque_n1", "color": get_session_state_value('custom_colors', DEFAULT_COLORS)['hors_marque']}, "impressions": {"title": "Impressions SEO Marque", "yaxis_title": "Impressions", "metric_n": "impressions_marque_n", "metric_n1": "impressions_marque_n1", "color": get_session_state_value('custom_colors', DEFAULT_COLORS)['impressions_marque']}}
            
            # Boucle pour afficher les graphiques globaux avec personnalisation
            for key, config in chart_configs.items():
                with st.expander(f"✏️ Personnaliser le graphique '{config['title']}'"):
                    st.session_state.chart_texts[key]['title'] = st.text_input("Titre du graphique", value=st.session_state.chart_texts[key]['title'], key=f"title_{key}")
                    st.session_state.chart_texts[key]['label_n1'] = st.text_input("Libellé Période N-1", value=st.session_state.chart_texts[key]['label_n1'], key=f"label_n1_{key}")
                    st.session_state.chart_texts[key]['label_n'] = st.text_input("Libellé Période N", value=st.session_state.chart_texts[key]['label_n'], key=f"label_n_{key}")
                
                fig = create_generic_bar_chart(metrics, st.session_state.chart_texts[key], get_session_state_value('style_options', DEFAULT_STYLE_OPTIONS), config)
                st.plotly_chart(fig, use_container_width=True)

            # Logique pour les graphiques mensuels
            monthly_data = get_monthly_breakdown(df_queries, df_pages, periode_n_dates, periode_n1_dates, regex_pattern)
            if monthly_data is not None and len(monthly_data) > 1:
                st.markdown("---"); st.markdown("### 📊 Évolution Mensuelle Détaillée")
                monthly_chart_configs = {"global": {"key": "monthly_global", "title": "Trafic SEO Global", "yaxis_title": "Clics", "metric_n": "total_clics", "metric_n1": "total_clics_n1", "color": get_session_state_value('custom_colors', DEFAULT_COLORS)['global_seo']}, "marque": {"key": "monthly_marque", "title": "Trafic SEO Marque", "yaxis_title": "Clics", "metric_n": "clics_marque", "metric_n1": "clics_marque_n1", "color": get_session_state_value('custom_colors', DEFAULT_COLORS)['marque_clics']}, "hors_marque": {"key": "monthly_hors_marque", "title": "Trafic SEO Hors-Marque", "yaxis_title": "Clics", "metric_n": "clics_hors_marque", "metric_n1": "clics_hors_marque_n1", "color": get_session_state_value('custom_colors', DEFAULT_COLORS)['hors_marque']}, "impressions": {"key": "monthly_impressions", "title": "Impressions SEO Marque", "yaxis_title": "Impressions", "metric_n": "impressions_marque", "metric_n1": "impressions_marque_n1", "color": get_session_state_value('custom_colors', DEFAULT_COLORS)['impressions_marque']}}
                
                for config in monthly_chart_configs.values():
                    with st.expander(f"✏️ Personnaliser le graphique '{config['title']} (Mensuel)'"):
                        st.session_state.chart_texts[config['key']]['title'] = st.text_input("Titre du graphique", value=st.session_state.chart_texts[config['key']]['title'], key=f"title_{config['key']}")
                    
                    fig = create_monthly_breakdown_chart(monthly_data, st.session_state.chart_texts[config['key']], get_session_state_value('style_options', DEFAULT_STYLE_OPTIONS), config)
                    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
