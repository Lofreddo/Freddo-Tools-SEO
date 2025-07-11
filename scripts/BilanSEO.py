import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
from pandas.tseries.offsets import MonthEnd

# --- Configuration de la Page ---
st.set_page_config(
    page_title="Dashboard SEO - Générateur de Graphiques",
    page_icon="📊",
    layout="wide"
)

# --- Valeurs par Défaut (utilisées pour pré-remplir les options locales) ---
DEFAULT_COLORS = {
    'global_seo': '#2563EB', 'marque_clics': '#1E40AF', 'impressions_marque': '#3730A3',
    'hors_marque': '#2563EB', 'pie_marque': '#1E40AF', 'pie_hors_marque': '#A5B4FC',
    'evolution_positive': '#10B981', 'evolution_negative': '#EF4444',
    'secondary_light': '#A5B4FC'
}
DEFAULT_STYLE_OPTIONS = {
    'font_family': 'Arial', 'title_font_size': 18, 'axis_font_size': 12, 'bar_text_font_size': 12
}
DEFAULT_TITLES = {
    'evolution_summary': "Synthèse des Évolutions (%)",
    'pie_chart': "Répartition des Clics (basée sur Requêtes)",
    'global_clicks': "Trafic SEO Global",
    'brand_clicks': "Trafic SEO Marque",
    'non_brand_clicks': "Trafic SEO Hors-Marque",
    'brand_impressions': "Impressions SEO Marque",
    'monthly_evolution': "Évolution Mensuelle",
    'axis_clicks': "Clics",
    'axis_impressions': "Impressions",
    'axis_period': "Période",
    'axis_month': "Mois",
    'legend_n': "Période N",
    'legend_n1': "Période N-1",
    'metric_total_clicks': "Total Clics",
    'metric_brand_clicks': "Clics Marque",
    'metric_non_brand_clicks': "Clics Hors-Marque",
    'metric_total_impressions': "Total Impressions"
}


# --- Fonctions Utilitaires et de Traitement de Données (INCHANGÉES) ---
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
    final_df = pd.DataFrame(index=all_months); final_df.index.name = 'month'
    final_df = final_df.join(monthly_p_n if _df_pages is not None else monthly_q_n[['total_clics_q', 'total_impressions_q']].rename(columns={'total_clics_q': 'total_clics', 'total_impressions_q': 'total_impressions'}), how='left')
    final_df = final_df.join(monthly_q_n[['clics_marque', 'clics_hors_marque', 'impressions_marque']], how='left')
    if not monthly_q_n1.empty: final_df = final_df.join(monthly_q_n1.add_suffix('_n1').set_index(monthly_q_n1.index.map(lambda p: p.asfreq('M') + 12)), how='left')
    if not monthly_p_n1.empty: final_df = final_df.join(monthly_p_n1.add_suffix('_n1').set_index(monthly_p_n1.index.map(lambda p: p.asfreq('M') + 12)), how='left')
    final_df = final_df.fillna(0).reset_index(); final_df['month_label'] = final_df['month'].dt.strftime('%b %Y')
    return final_df

# --- Fonctions de Création de Graphiques ---
def create_evolution_chart(metrics, chart_title, labels, colors, style_options):
    evolutions = []
    if metrics['total_clics_n1'] > 0: evolutions.append({'Métrique': labels['total_clicks'], 'Évolution': ((metrics['total_clics_n'] - metrics['total_clics_n1']) / metrics['total_clics_n1'] * 100)})
    if metrics['clics_marque_n1'] > 0: evolutions.append({'Métrique': labels['brand_clicks'], 'Évolution': ((metrics['clics_marque_n'] - metrics['clics_marque_n1']) / metrics['clics_marque_n1'] * 100)})
    if metrics['clics_hors_marque_n1'] > 0: evolutions.append({'Métrique': labels['non_brand_clicks'], 'Évolution': ((metrics['clics_hors_marque_n'] - metrics['clics_hors_marque_n1']) / metrics['clics_hors_marque_n1'] * 100)})
    if metrics['total_impressions_n1'] > 0: evolutions.append({'Métrique': labels['total_impressions'], 'Évolution': ((metrics['total_impressions_n'] - metrics['total_impressions_n1']) / metrics['total_impressions_n1'] * 100)})
    
    if not evolutions: return go.Figure().update_layout(title="Pas de données pour calculer l'évolution")
    
    df_evo = pd.DataFrame(evolutions)
    bar_colors = [colors['positive'] if x >= 0 else colors['negative'] for x in df_evo['Évolution']]
    
    fig = go.Figure(data=[go.Bar(x=df_evo['Métrique'], y=df_evo['Évolution'], marker_color=bar_colors, text=[f"{x:+.1f}%" for x in df_evo['Évolution']], textposition='auto', textfont=dict(size=style_options['bar_text_font_size'], color='white'))])
    fig.update_layout(title=chart_title, font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, plot_bgcolor='white', yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black'))
    return fig

def create_pie_charts(metrics, base_title, colors, style_options):
    figs = []
    for period, legend in [('n1', DEFAULT_TITLES['legend_n1']), ('n', DEFAULT_TITLES['legend_n'])]:
        total = metrics[f'clics_marque_{period}'] + metrics[f'clics_hors_marque_{period}']
        if total > 0:
            labels = [f"Hors-Marque<br>{metrics[f'clics_hors_marque_{period}']:,} ({metrics[f'clics_hors_marque_{period}']/total*100:.1f}%)", f"Marque<br>{metrics[f'clics_marque_{period}']:,} ({metrics[f'clics_marque_{period}']/total*100:.1f}%)"]
            values = [metrics[f'clics_hors_marque_{period}'], metrics[f'clics_marque_{period}']]
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=[colors['hors_marque'], colors['marque']], hole=0.4, textinfo='label', textfont=dict(size=style_options['axis_font_size']))])
            fig.update_layout(title=f"{base_title} {legend}:<br>{metrics[f'nom_periode_{period}']}", height=450, font=dict(family=style_options['font_family']), title_font_size=style_options['title_font_size'])
            figs.append(fig)
        else:
            fig = go.Figure().update_layout(title=f"Pas de données pour la période {period.upper()}", height=450)
            figs.append(fig)
    return figs[0], figs[1]

# --- CORRIGÉ ---
def create_generic_bar_chart(metrics, config, chart_title, color, style_options):
    legend_n1, legend_n = DEFAULT_TITLES['legend_n1'], DEFAULT_TITLES['legend_n']
    
    # On utilise le dictionnaire 'metrics' complet et on extrait les valeurs via 'config'
    y_values = [metrics[config['metric_n1']], metrics[config['metric_n']]]
    text_values = [f"{y:,}" for y in y_values]
    
    fig = go.Figure(data=[go.Bar(
        x=[f"{legend_n1}<br>{metrics['nom_periode_n1']}", f"{legend_n}<br>{metrics['nom_periode_n']}"], 
        y=y_values, 
        marker_color=color, 
        text=text_values, 
        textposition='auto', 
        textfont=dict(size=style_options['bar_text_font_size'], color='white')
    )])
    
    fig.update_layout(
        title=chart_title, 
        xaxis_title=DEFAULT_TITLES['axis_period'], 
        yaxis_title=DEFAULT_TITLES[config['yaxis_key']], 
        font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), 
        title_font_size=style_options['title_font_size'], 
        height=500, 
        showlegend=False, 
        plot_bgcolor='white'
    )
    return fig

def create_monthly_breakdown_chart(monthly_data, chart_title, legends, colors, style_options, yaxis_title, custom_x_labels=None):
    x_axis_labels = custom_x_labels if custom_x_labels is not None else monthly_data['month_label']
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x_axis_labels, y=monthly_data['metric_n1'], name=legends['n1'], marker_color=colors['n1'], text=[f"{x:,.0f}" for x in monthly_data['metric_n1']], textposition='outside'))
    fig.add_trace(go.Bar(x=x_axis_labels, y=monthly_data['metric_n'], name=legends['n'], marker_color=colors['n'], text=[f"{x:,.0f}" for x in monthly_data['metric_n']], textposition='outside'))
    fig.update_layout(title=chart_title, xaxis_title=DEFAULT_TITLES['axis_month'], yaxis_title=yaxis_title, barmode='group', font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, plot_bgcolor='white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# --- Application Principale ---
def main():
    st.title("📊 Dashboard SEO - Générateur de Graphiques")
    st.markdown("**Analysez vos performances SEO en comparant des périodes de mois complets.**")
    
    st.markdown("---"); st.markdown("### 🏷️ Configuration"); regex_pattern = st.text_input("Regex Marque", value="weefin|wee fin")
    try: re.compile(regex_pattern)
    except re.error: st.error("❌ Regex invalide."); st.stop()
        
    st.markdown("---"); st.markdown("### 📥 Import des Données GSC")
    col1, col2 = st.columns(2)
    uploaded_file_queries = col1.file_uploader("1. Fichier 'Requêtes' (Obligatoire)", type=['xlsx', 'xls'])
    uploaded_file_pages = col2.file_uploader("2. Fichier 'Pages' (Recommandé)", type=['xlsx', 'xls'])

    if uploaded_file_queries:
        df_queries = load_data(uploaded_file_queries); st.success(f"✅ Fichier 'Requêtes' chargé ({len(df_queries):,} lignes).")
        df_pages = None
        if uploaded_file_pages: df_pages = load_data(uploaded_file_pages); st.success(f"✅ Fichier 'Pages' chargé ({len(df_pages):,} lignes).")
        else: st.warning("⚠️ Fichier 'Pages' non fourni. Les totaux seront moins précis.")
        today = datetime.now().date(); anchor_date = today.replace(day=1) - timedelta(days=1)
        st.info(f"💡 L'analyse se base sur les mois terminés. Date de référence: **{anchor_date.strftime('%d/%m/%Y')}**.")
        st.markdown("### 📅 Type de Comparaison"); comparison_mode = st.radio("Mode :", ["Périodes Consécutives", "Année sur Année (YoY)"], horizontal=True, key="comparison_mode")
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
            options_yoy = ["3 derniers mois complets"]
            selection_yoy = st.radio("Période (YoY) :", options_yoy, horizontal=True, key="yoy_period")
            if selection_yoy == "3 derniers mois complets":
                n_end = anchor_date; n_start = get_start_of_month(anchor_date, 2)
                n1_start = n_start.replace(year=n_start.year - 1); n1_end = n_end.replace(year=n_end.year - 1)
                periode_n_dates, periode_n1_dates = (n_start, n_end), (n1_start, n1_end)
                period_type = "3 derniers mois vs N-1 (YoY)"

        if periode_n_dates:
            st.markdown("---"); st.markdown("### 🔎 Périodes Sélectionnées")
            st.write(f"**Période N :** `{periode_n_dates[0].strftime('%d/%m/%Y')} - {periode_n_dates[1].strftime('%d/%m/%Y')}`")
            st.write(f"**Période N-1 :** `{periode_n1_dates[0].strftime('%d/%m/%Y')} - {periode_n1_dates[1].strftime('%d/%m/%Y')}`")
            metrics = process_data_for_periods(df_queries, df_pages, periode_n_dates, periode_n1_dates, regex_pattern)
            
            if metrics['total_clics_n'] == 0 and metrics['total_clics_n1'] == 0:
                st.warning("⚠️ Aucune donnée trouvée pour les périodes sélectionnées.")
            else:
                st.markdown("---"); st.markdown("### 📈 Analyse Globale sur la Période")

                with st.container(border=True):
                    with st.expander("✏️ Personnaliser ce graphique"):
                        st.subheader("Titres et Labels")
                        chart_title_evo = st.text_input("Titre", f"{DEFAULT_TITLES['evolution_summary']} - {period_type}", key="evo_title")
                        labels_evo = {
                            'total_clicks': st.text_input("Label Clics Totaux", DEFAULT_TITLES['metric_total_clicks'], key="evo_label_tc"),
                            'brand_clicks': st.text_input("Label Clics Marque", DEFAULT_TITLES['metric_brand_clicks'], key="evo_label_bc"),
                            'non_brand_clicks': st.text_input("Label Clics Hors-Marque", DEFAULT_TITLES['metric_non_brand_clicks'], key="evo_label_nbc"),
                            'total_impressions': st.text_input("Label Impressions", DEFAULT_TITLES['metric_total_impressions'], key="evo_label_ti")
                        }
                        st.subheader("Couleurs")
                        colors_evo = {
                            'positive': st.color_picker("Évolution Positive", DEFAULT_COLORS['evolution_positive'], key="evo_color_pos"),
                            'negative': st.color_picker("Évolution Négative", DEFAULT_COLORS['evolution_negative'], key="evo_color_neg")
                        }
                        st.subheader("Polices")
                        style_options_evo = {
                            'font_family': st.selectbox("Famille de police", ['Arial', 'Verdana', 'Helvetica', 'Garamond', 'Times New Roman'], index=0, key="evo_font"),
                            'title_font_size': st.slider("Taille du titre", 10, 30, DEFAULT_STYLE_OPTIONS['title_font_size'], key="evo_font_title"),
                            'axis_font_size': st.slider("Taille des axes", 8, 20, DEFAULT_STYLE_OPTIONS['axis_font_size'], key="evo_font_axis"),
                            'bar_text_font_size': st.slider("Texte sur les barres", 8, 20, DEFAULT_STYLE_OPTIONS['bar_text_font_size'], key="evo_font_bar")
                        }
                    fig_evo = create_evolution_chart(metrics, chart_title_evo, labels_evo, colors_evo, style_options_evo)
                    st.plotly_chart(fig_evo, use_container_width=True)

                with st.container(border=True):
                    with st.expander("✏️ Personnaliser ces graphiques"):
                        st.subheader("Titres et Labels")
                        base_title_pie = st.text_input("Titre de base", DEFAULT_TITLES['pie_chart'], key="pie_title")
                        st.subheader("Couleurs")
                        colors_pie = {
                            'marque': st.color_picker("Couleur Marque", DEFAULT_COLORS['pie_marque'], key="pie_color_brand"),
                            'hors_marque': st.color_picker("Couleur Hors-Marque", DEFAULT_COLORS['pie_hors_marque'], key="pie_color_nonbrand")
                        }
                        st.subheader("Polices")
                        style_options_pie = {
                            'font_family': st.selectbox("Famille de police", ['Arial', 'Verdana', 'Helvetica', 'Garamond', 'Times New Roman'], index=0, key="pie_font"),
                            'title_font_size': st.slider("Taille du titre", 10, 30, DEFAULT_STYLE_OPTIONS['title_font_size'], key="pie_font_title"),
                            'axis_font_size': st.slider("Taille texte camembert", 8, 20, DEFAULT_STYLE_OPTIONS['axis_font_size'], key="pie_font_text"),
                        }
                    pie1, pie2 = create_pie_charts(metrics, base_title_pie, colors_pie, style_options_pie)
                    col1, col2 = st.columns(2); col1.plotly_chart(pie1, use_container_width=True); col2.plotly_chart(pie2, use_container_width=True)

                chart_configs = {
                    "global": {"title_key": "global_clicks", "yaxis_key": "axis_clicks", "metric_n": "total_clics_n", "metric_n1": "total_clics_n1", "color_key": "global_seo"},
                    "marque": {"title_key": "brand_clicks", "yaxis_key": "axis_clicks", "metric_n": "clics_marque_n", "metric_n1": "clics_marque_n1", "color_key": "marque_clics"},
                    "hors_marque": {"title_key": "non_brand_clicks", "yaxis_key": "axis_clicks", "metric_n": "clics_hors_marque_n", "metric_n1": "clics_hors_marque_n1", "color_key": "hors_marque"},
                    "impressions": {"title_key": "brand_impressions", "yaxis_key": "axis_impressions", "metric_n": "impressions_marque_n", "metric_n1": "impressions_marque_n1", "color_key": "impressions_marque"}
                }
                for key, config in chart_configs.items():
                    with st.container(border=True):
                        with st.expander(f"✏️ Personnaliser le graphique : {DEFAULT_TITLES[config['title_key']]}"):
                            chart_title_bar = st.text_input("Titre", f"{DEFAULT_TITLES[config['title_key']]} ({DEFAULT_TITLES[config['yaxis_key']]}) - {period_type}", key=f"bar_title_{key}")
                            color_bar = st.color_picker("Couleur des barres", DEFAULT_COLORS[config['color_key']], key=f"bar_color_{key}")
                            style_options_bar = {
                                'font_family': st.selectbox("Famille de police", ['Arial', 'Verdana', 'Helvetica', 'Garamond', 'Times New Roman'], index=0, key=f"bar_font_{key}"),
                                'title_font_size': st.slider("Taille du titre", 10, 30, DEFAULT_STYLE_OPTIONS['title_font_size'], key=f"bar_font_title_{key}"),
                                'axis_font_size': st.slider("Taille des axes", 8, 20, DEFAULT_STYLE_OPTIONS['axis_font_size'], key=f"bar_font_axis_{key}"),
                                'bar_text_font_size': st.slider("Texte sur les barres", 8, 20, DEFAULT_STYLE_OPTIONS['bar_text_font_size'], key=f"bar_font_text_{key}")
                            }
                        # --- CORRIGÉ ---
                        # On passe le dictionnaire 'metrics' complet et la 'config'
                        fig_bar = create_generic_bar_chart(metrics, config, chart_title_bar, color_bar, style_options_bar)
                        st.plotly_chart(fig_bar, use_container_width=True)

                monthly_data = get_monthly_breakdown(df_queries, df_pages, periode_n_dates, periode_n1_dates, regex_pattern)
                if monthly_data is not None and not monthly_data.empty and len(monthly_data) > 1:
                    st.markdown("---"); st.markdown("### 📊 Évolution Mensuelle Détaillée")
                    with st.expander("✏️ Personnaliser les étiquettes des mois (appliqué à tous les graphiques mensuels)"):
                        editable_labels = monthly_data['month_label'].tolist()
                        cols = st.columns(len(editable_labels))
                        for i, label in enumerate(editable_labels):
                            editable_labels[i] = cols[i].text_input(f"Label Mois {i+1}", label, key=f"month_label_{i}")
                    
                    monthly_chart_configs = {
                        "global": {"title_key": "global_clicks", "yaxis_key": "axis_clicks", "metric_n": "total_clics", "metric_n1": "total_clics_n1", "color_key": "global_seo"},
                        "marque": {"title_key": "brand_clicks", "yaxis_key": "axis_clicks", "metric_n": "clics_marque", "metric_n1": "clics_marque_n1", "color_key": "marque_clics"},
                        "hors_marque": {"title_key": "non_brand_clicks", "yaxis_key": "axis_clicks", "metric_n": "clics_hors_marque", "metric_n1": "clics_hors_marque_n1", "color_key": "hors_marque"},
                        "impressions": {"title_key": "brand_impressions", "yaxis_key": "axis_impressions", "metric_n": "impressions_marque", "metric_n1": "impressions_marque_n1", "color_key": "impressions_marque"}
                    }
                    for key, config in monthly_chart_configs.items():
                        with st.container(border=True):
                             with st.expander(f"✏️ Personnaliser le graphique : {DEFAULT_TITLES[config['title_key']]} (Mensuel)"):
                                chart_title_monthly = st.text_input("Titre", f"{DEFAULT_TITLES[config['title_key']]} ({DEFAULT_TITLES['monthly_evolution']})", key=f"monthly_title_{key}")
                                st.subheader("Légendes")
                                legends_monthly = {
                                    'n': st.text_input("Légende Période N", DEFAULT_TITLES['legend_n'], key=f"monthly_leg_n_{key}"),
                                    'n1': st.text_input("Légende Période N-1", DEFAULT_TITLES['legend_n1'], key=f"monthly_leg_n1_{key}")
                                }
                                st.subheader("Couleurs")
                                colors_monthly = {
                                    'n': st.color_picker("Couleur Période N", DEFAULT_COLORS[config['color_key']], key=f"monthly_color_n_{key}"),
                                    'n1': st.color_picker("Couleur Période N-1", DEFAULT_COLORS['secondary_light'], key=f"monthly_color_n1_{key}")
                                }
                                st.subheader("Polices")
                                style_options_monthly = {
                                    'font_family': st.selectbox("Famille de police", ['Arial', 'Verdana', 'Helvetica', 'Garamond', 'Times New Roman'], index=0, key=f"monthly_font_{key}"),
                                    'title_font_size': st.slider("Taille du titre", 10, 30, DEFAULT_STYLE_OPTIONS['title_font_size'], key=f"monthly_font_title_{key}"),
                                    'axis_font_size': st.slider("Taille des axes", 8, 20, DEFAULT_STYLE_OPTIONS['axis_font_size'], key=f"monthly_font_axis_{key}"),
                                }
                             monthly_data_subset = {'metric_n': monthly_data[config['metric_n']], 'metric_n1': monthly_data[config['metric_n1']]}
                             fig_monthly = create_monthly_breakdown_chart(monthly_data_subset, chart_title_monthly, legends_monthly, colors_monthly, style_options_monthly, DEFAULT_TITLES[config['yaxis_key']], custom_x_labels=editable_labels)
                             st.plotly_chart(fig_monthly, use_container_width=True)

if __name__ == "__main__":
    main()
