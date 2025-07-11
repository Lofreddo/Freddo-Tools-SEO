import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
import calendar
from pandas.tseries.offsets import MonthEnd

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
    if 'custom_colors' not in st.session_state: st.session_state.custom_colors = DEFAULT_COLORS.copy()
    return st.session_state.custom_colors

def get_style_options():
    if 'style_options' not in st.session_state: st.session_state.style_options = DEFAULT_STYLE_OPTIONS.copy()
    return st.session_state.style_options

# --- Fonctions Utilitaires et de Traitement de Données ---
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file)
    if "Date" in df.columns and "start_date" not in df.columns:
        df.rename(columns={"Date": "start_date"}, inplace=True)
    df['start_date'] = pd.to_datetime(df['start_date']).dt.date
    return df

def is_marque_query(query, regex_pattern):
    if pd.isna(query) or not regex_pattern: return False
    try: return bool(re.search(regex_pattern, str(query), re.IGNORECASE))
    except re.error: return False

def get_start_of_month(d, months_to_subtract=0):
    year, month = d.year, d.month; month -= months_to_subtract
    while month <= 0: month += 12; year -= 1
    return datetime(year, month, 1).date()

@st.cache_data
def process_data_for_periods(_df_queries, _df_pages, periode_n_dates, periode_n1_dates, regex_pattern):
    df_queries = _df_queries.copy()
    df_queries['is_marque'] = df_queries['query'].apply(lambda x: is_marque_query(x, regex_pattern))
    q_periode_n = df_queries[(df_queries['start_date'] >= periode_n_dates[0]) & (df_queries['start_date'] <= periode_n_dates[1])]
    q_periode_n1 = df_queries[(df_queries['start_date'] >= periode_n1_dates[0]) & (df_queries['start_date'] <= periode_n1_dates[1])]
    metrics = {
        'clics_marque_n': q_periode_n[q_periode_n['is_marque']]['clicks'].sum(),
        'clics_marque_n1': q_periode_n1[q_periode_n1['is_marque']]['clicks'].sum(),
        'clics_hors_marque_n': q_periode_n[~q_periode_n['is_marque']]['clicks'].sum(),
        'clics_hors_marque_n1': q_periode_n1[~q_periode_n1['is_marque']]['clicks'].sum(),
        'impressions_marque_n': q_periode_n[q_periode_n['is_marque']]['impressions'].sum(),
        'impressions_marque_n1': q_periode_n1[q_periode_n1['is_marque']]['impressions'].sum(),
        'nom_periode_n1': f"{periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}",
        'nom_periode_n': f"{periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')}"
    }
    if _df_pages is not None:
        df_pages = _df_pages.copy()
        p_periode_n = df_pages[(df_pages['start_date'] >= periode_n_dates[0]) & (df_pages['start_date'] <= periode_n_dates[1])]
        p_periode_n1 = df_pages[(df_pages['start_date'] >= periode_n1_dates[0]) & (df_pages['start_date'] <= periode_n1_dates[1])]
        metrics['total_clics_n'], metrics['total_clics_n1'] = p_periode_n['clicks'].sum(), p_periode_n1['clicks'].sum()
        metrics['total_impressions_n'], metrics['total_impressions_n1'] = p_periode_n['impressions'].sum(), p_periode_n1['impressions'].sum()
    else:
        metrics['total_clics_n'], metrics['total_clics_n1'] = q_periode_n['clicks'].sum(), q_periode_n1['clicks'].sum()
        metrics['total_impressions_n'], metrics['total_impressions_n1'] = q_periode_n['impressions'].sum(), q_periode_n1['impressions'].sum()
    return metrics

@st.cache_data
def get_monthly_breakdown(_df_queries, _df_pages, periode_n_dates, periode_n1_dates, regex_pattern):
    def aggregate_monthly(df, start_date, end_date, is_queries=False):
        df_period = df[(df['start_date'] >= start_date) & (df['start_date'] <= end_date)].copy()
        if df_period.empty: return pd.DataFrame()
        df_period['month'] = pd.to_datetime(df_period['start_date']).dt.to_period('M')
        agg_dict = {'clicks': 'sum', 'impressions': 'sum'}
        if is_queries:
            df_period['is_marque'] = df_period['query'].apply(lambda x: is_marque_query(x, regex_pattern))
            marque_agg = df_period[df_period['is_marque']].groupby('month').agg(agg_dict).rename(columns={'clicks': 'clics_marque', 'impressions': 'impressions_marque'})
            hors_marque_agg = df_period[~df_period['is_marque']].groupby('month').agg(agg_dict).rename(columns={'clicks': 'clics_hors_marque', 'impressions': 'impressions_hors_marque'})
            total_agg = df_period.groupby('month').agg(agg_dict).rename(columns={'clicks': 'total_clics_q', 'impressions': 'total_impressions_q'})
            return total_agg.join(marque_agg, how='left').join(hors_marque_agg, how='left').fillna(0)
        else:
            return df_period.groupby('month').agg(agg_dict).rename(columns={'clicks': 'total_clics', 'impressions': 'total_impressions'})

    monthly_q_n = aggregate_monthly(_df_queries, periode_n_dates[0], periode_n_dates[1], is_queries=True)
    monthly_q_n1 = aggregate_monthly(_df_queries, periode_n1_dates[0], periode_n1_dates[1], is_queries=True)

    monthly_p_n, monthly_p_n1 = (aggregate_monthly(_df_pages, d[0], d[1]) if _df_pages is not None else pd.DataFrame() for d in [periode_n_dates, periode_n1_dates])
    
    all_months = pd.period_range(start=periode_n_dates[0], end=periode_n_dates[1], freq='M')
    final_df = pd.DataFrame(index=all_months)
    final_df.index.name = 'month'
    
    # Données N
    final_df = final_df.join(monthly_p_n if _df_pages is not None else monthly_q_n[['total_clics_q', 'total_impressions_q']].rename(columns={'total_clics_q': 'total_clics', 'total_impressions_q': 'total_impressions'}), how='left')
    final_df = final_df.join(monthly_q_n[['clics_marque', 'clics_hors_marque', 'impressions_marque']], how='left')
    
    # Données N-1 (avec décalage temporel)
    if not monthly_q_n1.empty:
        monthly_q_n1.index = monthly_q_n1.index.map(lambda p: p.asfreq('M') + 12)
        final_df = final_df.join(monthly_q_n1.add_suffix('_n1'), how='left')
    if not monthly_p_n1.empty:
        monthly_p_n1.index = monthly_p_n1.index.map(lambda p: p.asfreq('M') + 12)
        final_df = final_df.join(monthly_p_n1.add_suffix('_n1'), how='left')
    
    final_df = final_df.fillna(0); final_df['month_label'] = final_df['month'].dt.strftime('%b %Y')
    return final_df

# --- Fonctions de Création de Graphiques ---
def create_evolution_chart(metrics, period_type, style_options):
    COLORS, evolutions = get_colors(), []
    if metrics['total_clics_n1'] > 0: evolutions.append({'Métrique': 'Total Clics', 'Évolution': ((metrics['total_clics_n'] - metrics['total_clics_n1']) / metrics['total_clics_n1'] * 100)})
    if metrics['clics_marque_n1'] > 0: evolutions.append({'Métrique': 'Clics Marque', 'Évolution': ((metrics['clics_marque_n'] - metrics['clics_marque_n1']) / metrics['clics_marque_n1'] * 100)})
    if metrics['clics_hors_marque_n1'] > 0: evolutions.append({'Métrique': 'Clics Hors-Marque', 'Évolution': ((metrics['clics_hors_marque_n'] - metrics['clics_hors_marque_n1']) / metrics['clics_hors_marque_n1'] * 100)})
    if metrics['total_impressions_n1'] > 0: evolutions.append({'Métrique': 'Total Impressions', 'Évolution': ((metrics['total_impressions_n'] - metrics['total_impressions_n1']) / metrics['total_impressions_n1'] * 100)})
    if not evolutions: return None
    df_evo = pd.DataFrame(evolutions); colors = [COLORS['evolution_positive'] if x >= 0 else COLORS['evolution_negative'] for x in df_evo['Évolution']]
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
            fig.update_layout(title=f"Répartition (basée sur Requêtes) {title_suffix}: {metrics[f'nom_periode_{period}']}", height=450, font=dict(family=style_options['font_family']), title_font_size=style_options['title_font_size'])
            figs.append(fig)
        else: figs.append(go.Figure().update_layout(title=f"Pas de données pour la période {period.upper()}", height=450))
    return figs[0], figs[1]

def create_generic_bar_chart(metrics, period_type, style_options, config):
    fig = go.Figure(data=[go.Bar(x=[f"Période N-1<br>{metrics['nom_periode_n1']}", f"Période N<br>{metrics['nom_periode_n']}"], y=[metrics[config['metric_n1']], metrics[config['metric_n']]], marker_color=config['color'], text=[f"{metrics[config['metric_n1']]:,}", f"{metrics[config['metric_n']]:,}"], textposition='auto', textfont=dict(size=style_options['bar_text_font_size'], color='white'))])
    fig.update_layout(title=f"{config['title']} ({config['yaxis_title']}) - {period_type}", xaxis_title="Période", yaxis_title=config['yaxis_title'], font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, showlegend=False, plot_bgcolor='white')
    return fig

def create_monthly_breakdown_chart(monthly_data, style_options, config):
    COLORS = get_colors()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_data['month_label'], y=monthly_data[config['metric_n1']], name='Période N-1', marker_color=COLORS['secondary_light'], text=[f"{x:,.0f}" for x in monthly_data[config['metric_n1']]], textposition='outside'))
    fig.add_trace(go.Bar(x=monthly_data['month_label'], y=monthly_data[config['metric_n']], name='Période N', marker_color=config['color'], text=[f"{x:,.0f}" for x in monthly_data[config['metric_n']]], textposition='outside'))
    fig.update_layout(title=f"{config['title']} (Évolution Mensuelle)", xaxis_title="Mois", yaxis_title=config['yaxis_title'], barmode='group', font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, plot_bgcolor='white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def show_chart_customization():
    with st.expander("🎨 Personnalisation des Graphiques", expanded=False): pass

# --- Application Principale ---

def main():
    st.title("📊 Dashboard SEO - Générateur de Graphiques")
    st.markdown("**Analysez vos performances SEO en comparant des périodes de mois complets.**")
    
    show_chart_customization()
    
    st.markdown("---"); st.markdown("### 🏷️ Configuration"); regex_pattern = st.text_input("Regex Marque", value="weefin|wee fin")
    try: re.compile(regex_pattern)
    except re.error: st.error("❌ Regex invalide."); st.stop()
        
    st.markdown("---"); st.markdown("### 📥 Import des Données GSC")
    col1, col2 = st.columns(2)
    uploaded_file_queries = col1.file_uploader("1. Fichier 'Requêtes' (Obligatoire)", type=['xlsx', 'xls'])
    uploaded_file_pages = col2.file_uploader("2. Fichier 'Pages' (Recommandé)", type=['xlsx', 'xls'])

    if uploaded_file_queries:
        df_queries = load_data(uploaded_file_queries)
        st.success(f"✅ Fichier 'Requêtes' chargé ({len(df_queries):,} lignes).")
        
        df_pages = None
        if uploaded_file_pages:
            df_pages = load_data(uploaded_file_pages); st.success(f"✅ Fichier 'Pages' chargé ({len(df_pages):,} lignes).")
        else:
            st.warning("⚠️ Fichier 'Pages' non fourni. Les totaux seront moins précis.")

        today = datetime.now().date(); anchor_date = today.replace(day=1) - timedelta(days=1)
        st.info(f"💡 L'analyse se base sur les mois terminés. Date de référence: **{anchor_date.strftime('%d/%m/%Y')}**.")
        
        st.markdown("### 📅 Type de Comparaison"); comparison_mode = st.radio("Mode :", ["Périodes Consécutives", "Année sur Année (YoY)"], horizontal=True)
        periode_n_dates = None
        
        if comparison_mode == "Périodes Consécutives":
            options = {"3 derniers mois complets": 3, "6 derniers mois complets": 6, "Dernier mois complet": 1}
            selection = st.radio("Période :", options.keys(), horizontal=True, key="consecutive_period")
            months = options[selection]
            n_end = anchor_date; n_start = get_start_of_month(anchor_date, months - 1)
            n1_end = n_start - timedelta(days=1); n1_start = get_start_of_month(n1_end, months - 1)
            periode_n_dates, periode_n1_dates = (n_start, n_end), (n1_start, n1_end)
            period_type = f"{selection} vs Précédent"
        else:
            options_yoy = ["3 derniers mois complets", "Sélection Personnalisée"]
            selection_yoy = st.radio("Période (YoY) :", options_yoy, horizontal=True, key="yoy_period")
            if selection_yoy == "3 derniers mois complets":
                n_end = anchor_date; n_start = get_start_of_month(anchor_date, 2)
                n1_start = n_start.replace(year=n_start.year - 1); n1_end = n_end.replace(year=n_end.year - 1)
                periode_n_dates, periode_n1_dates = (n_start, n_end), (n1_start, n1_end)
                period_type = "3 derniers mois vs N-1 (YoY)"
            else:
                with st.expander("📅 Définir une période personnalisée (YoY)", expanded=True):
                    # ... (logique personnalisée)
                    pass

        if periode_n_dates:
            st.markdown("---"); st.markdown("### 🔎 Périodes Sélectionnées")
            st.write(f"**Période N :** `{periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')}`")
            st.write(f"**Période N-1 :** `{periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}`")
            
            metrics = process_data_for_periods(df_queries, df_pages, periode_n_dates, periode_n1_dates, regex_pattern)
            
            if metrics['total_clics_n'] == 0 and metrics['total_clics_n1'] == 0:
                st.warning("⚠️ Aucune donnée trouvée pour les périodes sélectionnées.")
            else:
                st.markdown("---"); st.markdown("### 📈 Analyse Globale sur la Période")
                
                # CORRECTION: Définition correcte des clés
                chart_configs = {
                    "global": {"title": "Trafic SEO Global", "yaxis_title": "Clics", "metric_n": "total_clics_n", "metric_n1": "total_clics_n1", "color": get_colors()['global_seo']},
                    "marque": {"title": "Trafic SEO Marque", "yaxis_title": "Clics", "metric_n": "clics_marque_n", "metric_n1": "clics_marque_n1", "color": get_colors()['marque_clics']},
                    "hors_marque": {"title": "Trafic SEO Hors-Marque", "yaxis_title": "Clics", "metric_n": "clics_hors_marque_n", "metric_n1": "clics_hors_marque_n1", "color": get_colors()['hors_marque']},
                    "impressions": {"title": "Impressions SEO Marque", "yaxis_title": "Impressions", "metric_n": "impressions_marque_n", "metric_n1": "impressions_marque_n1", "color": get_colors()['impressions_marque']}
                }
                
                st.plotly_chart(create_evolution_chart(metrics, period_type, get_style_options()), use_container_width=True)
                pie1, pie2 = create_pie_charts(metrics, get_style_options())
                col1, col2 = st.columns(2); col1.plotly_chart(pie1, use_container_width=True); col2.plotly_chart(pie2, use_container_width=True)
                
                # CORRECTION: Appel simplifié
                for config in chart_configs.values():
                    st.plotly_chart(create_generic_bar_chart(metrics, period_type, get_style_options(), config), use_container_width=True)

                monthly_data = get_monthly_breakdown(df_queries, df_pages, periode_n_dates, periode_n1_dates, regex_pattern)
                if monthly_data is not None and not monthly_data.empty and len(monthly_data) > 1:
                    st.markdown("---"); st.markdown("### 📊 Évolution Mensuelle Détaillée")
                    
                    monthly_chart_configs = {
                        "global": {"title": "Trafic SEO Global", "yaxis_title": "Clics", "metric_n": "total_clics", "metric_n1": "total_clics_n1", "color": get_colors()['global_seo']},
                        "marque": {"title": "Trafic SEO Marque", "yaxis_title": "Clics", "metric_n": "clics_marque", "metric_n1": "clics_marque_n1", "color": get_colors()['marque_clics']},
                        "hors_marque": {"title": "Trafic SEO Hors-Marque", "yaxis_title": "Clics", "metric_n": "clics_hors_marque", "metric_n1": "clics_hors_marque_n1", "color": get_colors()['hors_marque']},
                        "impressions": {"title": "Impressions SEO Marque", "yaxis_title": "Impressions", "metric_n": "impressions_marque", "metric_n1": "impressions_marque_n1", "color": get_colors()['impressions_marque']}
                    }
                    
                    for config in monthly_chart_configs.values():
                        st.plotly_chart(create_monthly_breakdown_chart(monthly_data, get_style_options(), config), use_container_width=True)

if __name__ == "__main__":
    main()
