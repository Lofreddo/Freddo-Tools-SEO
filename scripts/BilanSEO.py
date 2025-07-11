import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

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
    'evolution_positive': '#10B981', 'evolution_negative': '#EF4444',
    'secondary_light': '#A5B4FC', 'secondary_dark': '#2563EB'
}
DEFAULT_LAYOUT_OPTIONS = {
    'font_family': 'Arial, sans-serif', 'chart_height': 500, 'plot_bgcolor': '#FFFFFF',
    'show_text_on_bars': True, 'legend_orientation': 'h'
}
FONT_OPTIONS = [
    'Arial, sans-serif', 'Verdana, sans-serif', 'Tahoma, sans-serif', 
    'Trebuchet MS, sans-serif', 'Georgia, serif', 'Times New Roman, serif', 
    'Courier New, monospace'
]

# --- GESTION DE L'ÉTAT DE SESSION ---
def get_colors():
    if 'custom_colors' not in st.session_state:
        st.session_state.custom_colors = DEFAULT_COLORS.copy()
    return st.session_state.custom_colors

def get_layout_options():
    if 'custom_layout' not in st.session_state:
        st.session_state.custom_layout = DEFAULT_LAYOUT_OPTIONS.copy()
    return st.session_state.custom_layout

# --- FONCTIONS UTILITAIRES ET TRAITEMENT DES DONNÉES ---

@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file)
    required_cols = ['start_date', 'query', 'clicks', 'impressions']
    if not all(col in df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df.columns]
        st.error(f"Colonnes requises manquantes : {', '.join(missing)}")
        return None
    df['start_date'] = pd.to_datetime(df['start_date']).dt.date
    return df

def is_marque_query(query, regex_pattern):
    if pd.isna(query) or not regex_pattern: return False
    try: return bool(re.search(regex_pattern, str(query), re.IGNORECASE))
    except re.error: return False

def get_predefined_periods():
    today = datetime.now().date()
    return {
        "7_derniers_jours": ("7 derniers jours", (today - timedelta(days=6), today), (today - timedelta(days=13), today - timedelta(days=7))),
        "28_derniers_jours": ("28 derniers jours", (today - timedelta(days=27), today), (today - timedelta(days=55), today - timedelta(days=28))),
        "3_derniers_mois": ("3 derniers mois", (today - timedelta(days=89), today), (today - timedelta(days=179), today - timedelta(days=90))),
        "6_derniers_mois": ("6 derniers mois", (today - timedelta(days=179), today), (today - timedelta(days=359), today - timedelta(days=180))),
    }

def format_period_name(start, end):
    return f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}"

def calculate_default_periods(max_date_in_file):
    last_day = max_date_in_file
    if max_date_in_file.day < 28 : # Si on est en début de mois, prendre le trimestre précédent
        last_day = max_date_in_file.replace(day=1) - timedelta(days=1)
    
    end_n = last_day
    start_n = (end_n.replace(day=1) - relativedelta(months=2)).replace(day=1)
    end_n1 = start_n - timedelta(days=1)
    start_n1 = (end_n1.replace(day=1) - relativedelta(months=2)).replace(day=1)
    return start_n, end_n, start_n1, end_n1

@st.cache_data
def process_data_for_periods(_df, periode_n_dates, periode_n1_dates, regex_pattern):
    df = _df.copy()
    df['is_marque'] = df['query'].apply(lambda q: is_marque_query(q, regex_pattern))
    periode_n = df[(df['start_date'] >= periode_n_dates[0]) & (df['start_date'] <= periode_n_dates[1])]
    periode_n1 = df[(df['start_date'] >= periode_n1_dates[0]) & (df['start_date'] <= periode_n1_dates[1])]
    metrics = {
        'total_clics_n1': periode_n1['clicks'].sum(), 'total_clics_n': periode_n['clicks'].sum(),
        'clics_marque_n1': periode_n1[periode_n1['is_marque']]['clicks'].sum(),
        'clics_marque_n': periode_n[periode_n['is_marque']]['clicks'].sum(),
        'clics_hors_marque_n1': periode_n1[~periode_n1['is_marque']]['clicks'].sum(),
        'clics_hors_marque_n': periode_n[~periode_n['is_marque']]['clicks'].sum(),
        'impressions_marque_n1': periode_n1[periode_n1['is_marque']]['impressions'].sum(),
        'impressions_marque_n': periode_n[periode_n['is_marque']]['impressions'].sum(),
        'total_impressions_n1': periode_n1['impressions'].sum(),
        'total_impressions_n': periode_n['impressions'].sum(),
        'nom_periode_n1': format_period_name(*periode_n1_dates),
        'nom_periode_n': format_period_name(*periode_n_dates)
    }
    return metrics

@st.cache_data
def process_monthly_data(_df, year_n, year_n1, regex_pattern):
    df = _df.copy()
    if 'year' not in df.columns:
        df['year'] = pd.to_datetime(df['start_date']).dt.year
    if 'month' not in df.columns:
        df['month'] = pd.to_datetime(df['start_date']).dt.month
    df['is_marque'] = df['query'].apply(lambda q: is_marque_query(q, regex_pattern))
    data_n = df[df['year'] == year_n]
    data_n1 = df[df['year'] == year_n1]
    comparable_months = sorted(list(set(data_n['month'].unique()) & set(data_n1['month'].unique())))
    if not comparable_months: return None
        
    month_names = {i: n for i, n in enumerate(['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'], 1)}
    monthly_data = {
        'months': [month_names[m] for m in comparable_months],
        'year_n': year_n, 'year_n1': year_n1, 'months_count': len(comparable_months),
        'total_clics_n': [], 'total_clics_n1': [], 'clics_marque_n': [], 'clics_marque_n1': [],
        'clics_hors_marque_n': [], 'clics_hors_marque_n1': [], 'impressions_marque_n': [], 'impressions_marque_n1': [],
    }
    
    for month in comparable_months:
        month_data_n = data_n[data_n['month'] == month]
        monthly_data['total_clics_n'].append(month_data_n['clicks'].sum())
        monthly_data['clics_marque_n'].append(month_data_n[month_data_n['is_marque']]['clicks'].sum())
        monthly_data['clics_hors_marque_n'].append(month_data_n[~month_data_n['is_marque']]['clicks'].sum())
        monthly_data['impressions_marque_n'].append(month_data_n[month_data_n['is_marque']]['impressions'].sum())
        
        month_data_n1 = data_n1[data_n1['month'] == month]
        monthly_data['total_clics_n1'].append(month_data_n1['clicks'].sum())
        monthly_data['clics_marque_n1'].append(month_data_n1[month_data_n1['is_marque']]['clicks'].sum())
        monthly_data['clics_hors_marque_n1'].append(month_data_n1[~month_data_n1['is_marque']]['clicks'].sum())
        monthly_data['impressions_marque_n1'].append(month_data_n1[month_data_n1['is_marque']]['impressions'].sum())
    return monthly_data

# --- FONCTIONS DE CRÉATION DE GRAPHIQUES ---
def create_base_layout(title, yaxis_title, period_type=""):
    opts = get_layout_options()
    return go.Layout(
        title=f"{title} - {period_type}", xaxis_title="Période", yaxis_title=yaxis_title,
        font=dict(size=12, family=opts['font_family']), height=opts['chart_height'],
        plot_bgcolor=opts['plot_bgcolor'], showlegend=False
    )

def create_comparison_bar_chart(metrics, y_key, color, title, period_type, yaxis_title="Clics"):
    opts = get_layout_options()
    fig = go.Figure()
    y_vals = [metrics[f'{y_key}_n1'], metrics[f'{y_key}_n']]
    text = [f"{v:,}" for v in y_vals] if opts['show_text_on_bars'] else None
    fig.add_trace(go.Bar(
        x=[f"Période N-1<br>{metrics['nom_periode_n1']}", f"Période N<br>{metrics['nom_periode_n']}"],
        y=y_vals, marker_color=color, text=text, textposition='auto', textfont=dict(size=14, color='white')
    ))
    fig.update_layout(create_base_layout(title, yaxis_title, period_type))
    return fig

def create_monthly_bar_chart(data, y_key, color_n, color_n1, title, yaxis_title="Clics"):
    opts = get_layout_options()
    fig = go.Figure()
    text_n1 = [f"{v:,}" for v in data[f'{y_key}_n1']] if opts['show_text_on_bars'] else None
    text_n = [f"{v:,}" for v in data[f'{y_key}_n']] if opts['show_text_on_bars'] else None
    fig.add_trace(go.Bar(
        x=data['months'], y=data[f'{y_key}_n1'], name=f"{data['year_n1']}",
        marker_color=color_n1, text=text_n1, textposition='auto', textfont=dict(size=11)
    ))
    fig.add_trace(go.Bar(
        x=data['months'], y=data[f'{y_key}_n'], name=f"{data['year_n']}",
        marker_color=color_n, text=text_n, textposition='auto', textfont=dict(size=11)
    ))
    fig.update_layout(
        create_base_layout(f"{title} - {data['year_n1']} vs {data['year_n']}", yaxis_title, f"{data['months_count']} mois"),
        barmode='group', showlegend=True,
        legend=dict(orientation=opts['legend_orientation'], yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def create_evolution_chart(metrics, period_type=""):
    COLORS, opts = get_colors(), get_layout_options()
    def calc_evo(n, n1): return ((n - n1) / n1 * 100) if n1 > 0 else 0
    evolutions = [
        {'Métrique': 'Total Clics', 'Évolution': calc_evo(metrics['total_clics_n'], metrics['total_clics_n1'])},
        {'Métrique': 'Clics Marque', 'Évolution': calc_evo(metrics['clics_marque_n'], metrics['clics_marque_n1'])},
        {'Métrique': 'Clics Hors-Marque', 'Évolution': calc_evo(metrics['clics_hors_marque_n'], metrics['clics_hors_marque_n1'])},
        {'Métrique': 'Impressions Marque', 'Évolution': calc_evo(metrics['impressions_marque_n'], metrics['impressions_marque_n1'])}
    ]
    df_evo = pd.DataFrame(evolutions)
    colors = [COLORS['evolution_positive'] if x >= 0 else COLORS['evolution_negative'] for x in df_evo['Évolution']]
    fig = go.Figure(data=[go.Bar(
        x=df_evo['Métrique'], y=df_evo['Évolution'], marker_color=colors,
        text=[f"{x:+.1f}%" for x in df_evo['Évolution']], textposition='auto', textfont=dict(size=14, color='white')
    )])
    fig.update_layout(
        create_base_layout("Synthèse des Évolutions (%)", "Évolution (%)", f"N vs N-1 - {period_type}"),
        yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black')
    )
    return fig

def create_pie_charts(metrics, period_type=""):
    COLORS, opts = get_colors(), get_layout_options()
    def create_single_pie(clics_m, clics_hm, title):
        total = clics_m + clics_hm
        pct_m = (clics_m / total * 100) if total > 0 else 0
        pct_hm = (clics_hm / total * 100) if total > 0 else 0
        fig = go.Figure(data=[go.Pie(
            labels=[f'Hors-Marque<br>{clics_hm:,} ({pct_hm:.1f}%)', f'Marque<br>{clics_m:,} ({pct_m:.1f}%)'],
            values=[clics_hm, clics_m], marker_colors=[COLORS['pie_hors_marque'], COLORS['pie_marque']],
            hole=0.4, textinfo='label', textposition='auto', textfont=dict(size=12, family=opts['font_family'])
        )])
        fig.update_layout(
            title=title, height=opts['chart_height'] - 50,
            font=dict(size=10, family=opts['font_family'])
        )
        return fig
    fig1 = create_single_pie(metrics['clics_marque_n1'], metrics['clics_hors_marque_n1'], f"Répartition N-1: {metrics['nom_periode_n1']}")
    fig2 = create_single_pie(metrics['clics_marque_n'], metrics['clics_hors_marque_n'], f"Répartition N: {metrics['nom_periode_n']}")
    return fig1, fig2

# --- INTERFACE UTILISATEUR (UI) ---
def show_customization_options():
    st.sidebar.title("🎨 Options de Personnalisation")
    with st.sidebar.expander("Mise en page", expanded=True):
        opts = get_layout_options()
        opts['font_family'] = st.selectbox("Police", FONT_OPTIONS, index=FONT_OPTIONS.index(opts['font_family']))
        opts['chart_height'] = st.slider("Hauteur (px)", 400, 1000, opts['chart_height'])
        opts['plot_bgcolor'] = st.color_picker("Couleur de fond", opts['plot_bgcolor'])
        opts['show_text_on_bars'] = st.toggle("Afficher valeurs sur barres", value=opts['show_text_on_bars'])
        opts['legend_orientation'] = 'h' if st.radio("Légende (mensuel)", ["Horizontale", "Verticale"], index=0 if opts['legend_orientation'] == 'h' else 1) == "Horizontale" else 'v'
        st.session_state.custom_layout = opts

    with st.sidebar.expander("Couleurs", expanded=False):
        colors = get_colors()
        for key in DEFAULT_COLORS.keys():
            colors[key] = st.color_picker(key.replace('_', ' ').title(), colors[key])
        st.session_state.custom_colors = colors
        if st.button("Réinitialiser les couleurs"):
            st.session_state.custom_colors = DEFAULT_COLORS.copy()
            st.rerun()

def main():
    st.title("📊 Dashboard SEO - Générateur de Graphiques")
    st.markdown("**Analysez vos performances SEO avec des visualisations personnalisées.**")

    show_customization_options()
    
    st.markdown("### 🏷️ 1. Configuration de la Marque")
    regex_pattern = st.text_input("Regex pour requêtes de marque", "weefin|wee fin", help="Ex: 'ma_marque|ma marque'")
    if not regex_pattern: st.warning("Veuillez saisir une regex."); st.stop()

    st.markdown("### 📂 2. Import des Données")
    uploaded_file = st.file_uploader("Fichier Google Search Console (Excel)", type=['xlsx', 'xls'])
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is None: st.stop()
        
        st.success(f"Fichier chargé avec succès! ({len(df):,} lignes)")
        
        min_date_in_file = df['start_date'].min()
        max_date_in_file = df['start_date'].max()
        st.info(f"Période couverte par le fichier : du **{format_period_name(min_date_in_file, max_date_in_file)}**.")
        
        df['year'] = pd.to_datetime(df['start_date']).dt.year
        available_years = sorted(df['year'].unique(), reverse=True)

        st.markdown("### 📊 3. Type d'Analyse")
        analysis_type = st.radio("Type de comparaison :", ["Comparaison par Blocs/Périodes", "Comparaison Mensuelle (Année N vs N-1)"], horizontal=True)
        
        st.markdown("### 📅 4. Sélection des Périodes")
        
        if analysis_type == "Comparaison par Blocs/Périodes":
            period_options = get_predefined_periods()
            selected_key = st.selectbox("Choix période", list(period_options.keys()) + ["Personnalisée"], format_func=lambda k: period_options[k][0] if k != "Personnalisée" else "Personnalisée", index=1)
            
            if selected_key == "Personnalisée":
                default_start_n, default_end_n, default_start_n1, default_end_n1 = calculate_default_periods(max_date_in_file)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("##### Période N (actuelle)")
                    start_n = st.date_input("Début N", default_start_n, min_value=min_date_in_file, max_value=max_date_in_file)
                    end_n = st.date_input("Fin N", default_end_n, min_value=min_date_in_file, max_value=max_date_in_file)
                with col2:
                    st.markdown("##### Période N-1 (précédente)")
                    start_n1 = st.date_input("Début N-1", default_start_n1, min_value=min_date_in_file, max_value=max_date_in_file)
                    end_n1 = st.date_input("Fin N-1", default_end_n1, min_value=min_date_in_file, max_value=max_date_in_file)
                periode_n_dates, periode_n1_dates = (start_n, end_n), (start_n1, end_n1)
                period_type = "Personnalisée"
            else:
                period_type, periode_n_dates, periode_n1_dates = period_options[selected_key]
                st.info(f"**Période N**: {format_period_name(*periode_n_dates)} | **Période N-1**: {format_period_name(*periode_n1_dates)}")

            metrics = process_data_for_periods(df, periode_n_dates, periode_n1_dates, regex_pattern)
            
            if metrics['total_clics_n'] == 0 and metrics['total_clics_n1'] == 0:
                st.warning("Aucune donnée trouvée pour les périodes sélectionnées. Vérifiez vos dates."); st.stop()
            
            st.header("🚀 Résultats de l'Analyse par Blocs")
            COLORS = get_colors()
            st.plotly_chart(create_evolution_chart(metrics, period_type), use_container_width=True)
            pie1, pie2 = create_pie_charts(metrics, period_type)
            col1, col2 = st.columns(2)
            with col1: st.plotly_chart(pie1, use_container_width=True)
            with col2: st.plotly_chart(pie2, use_container_width=True)
            st.plotly_chart(create_comparison_bar_chart(metrics, 'total_clics', COLORS['global_seo'], "Trafic SEO Global", period_type), use_container_width=True)
            st.plotly_chart(create_comparison_bar_chart(metrics, 'clics_marque', COLORS['marque_clics'], "Trafic SEO Marque", period_type), use_container_width=True)
            st.plotly_chart(create_comparison_bar_chart(metrics, 'clics_hors_marque', COLORS['hors_marque'], "Trafic SEO Hors-Marque", period_type), use_container_width=True)
            st.plotly_chart(create_comparison_bar_chart(metrics, 'impressions_marque', COLORS['impressions_marque'], "Impressions SEO Marque", period_type, yaxis_title="Impressions"), use_container_width=True)
        
        else: # Analyse Mensuelle
            selected_year = st.selectbox("Choisissez l'année N :", available_years, index=0 if len(available_years) > 1 else 0)
            previous_year = selected_year - 1
            if previous_year not in available_years:
                st.warning(f"L'année précédente ({previous_year}) n'existe pas dans vos données. Impossible de comparer."); st.stop()
            
            st.info(f"Comparaison de chaque mois de **{selected_year}** avec le même mois de **{previous_year}**.")
            monthly_data = process_monthly_data(df, selected_year, previous_year, regex_pattern)

            if not monthly_data or monthly_data['months_count'] == 0:
                st.warning(f"Aucun mois comparable trouvé entre {previous_year} et {selected_year}."); st.stop()
            
            st.success(f"Analyse sur **{monthly_data['months_count']} mois comparable(s)** : {', '.join(monthly_data['months'])}")
            
            st.header("🚀 Résultats de l'Analyse Mensuelle")
            COLORS = get_colors()
            st.plotly_chart(create_monthly_bar_chart(monthly_data, 'total_clics', COLORS['secondary_dark'], COLORS['secondary_light'], "Trafic SEO Global par Mois"), use_container_width=True)
            st.plotly_chart(create_monthly_bar_chart(monthly_data, 'clics_marque', COLORS['marque_clics'], COLORS['secondary_light'], "Trafic SEO Marque par Mois"), use_container_width=True)
            st.plotly_chart(create_monthly_bar_chart(monthly_data, 'clics_hors_marque', COLORS['hors_marque'], COLORS['secondary_light'], "Trafic SEO Hors-Marque par Mois"), use_container_width=True)
            st.plotly_chart(create_monthly_bar_chart(monthly_data, 'impressions_marque', COLORS['impressions_marque'], COLORS['secondary_light'], "Impressions SEO Marque par Mois", yaxis_title="Impressions"), use_container_width=True)

if __name__ == "__main__":
    main()
