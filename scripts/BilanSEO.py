import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta

# --- Configuration de la Page ---
st.set_page_config(page_title="Dashboard SEO", page_icon="📊", layout="wide")

# --- Valeurs par Défaut (INCHANGÉES) ---
DEFAULT_COLORS = {'global_seo': '#2563EB', 'marque_clics': '#1E40AF', 'impressions_marque': '#3730A3','hors_marque': '#2563EB', 'pie_marque': '#1E40AF', 'pie_hors_marque': '#A5B4FC','evolution_positive': '#10B981', 'evolution_negative': '#EF4444','secondary_light': '#A5B4FC'}
DEFAULT_STYLE_OPTIONS = {'font_family': 'Arial', 'title_font_size': 18, 'axis_font_size': 12, 'bar_text_font_size': 12}
DEFAULT_TITLES = {'evolution_summary': "Synthèse des Évolutions (%)", 'pie_chart': "Répartition des Clics",'global_clicks': "Trafic SEO Global", 'brand_clicks': "Trafic SEO Marque",'non_brand_clicks': "Trafic SEO Hors-Marque", 'brand_impressions': "Impressions SEO Marque",'monthly_evolution': "Évolution Mensuelle", 'axis_clicks': "Clics",'axis_impressions': "Impressions", 'axis_period': "Période", 'axis_month': "Mois",'axis_evolution': "Évolution (%)", 'axis_metric': "Métrique", 'legend_n': "Période N",'legend_n1': "Période N-1", 'metric_total_clicks': "Total Clics",'metric_brand_clicks': "Clics Marque", 'metric_non_brand_clicks': "Clics Hors-Marque",'metric_total_impressions': "Total Impressions", 'pie_label_brand': "Marque",'pie_label_non_brand': "Hors-Marque",}

# --- Fonctions de Traitement de Données (STABLES) ---
@st.cache_data
def load_data(uploaded_file):
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file)
    except Exception:
        try:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Impossible de lire le fichier. Assurez-vous qu'il s'agit d'un fichier Excel ou CSV valide. Erreur: {e}")
            st.stop()
    
    if 'start_date' not in df.columns:
        st.error(f"La colonne 'start_date' est obligatoire et introuvable. Colonnes présentes : {df.columns.tolist()}")
        st.stop()
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
    def aggregate_monthly(df, start_date, end_date):
        df_period = df[(df['start_date'] >= start_date) & (df['start_date'] <= end_date)].copy()
        if df_period.empty: return pd.DataFrame()
        df_period['month_period'] = pd.to_datetime(df_period['start_date']).dt.to_period('M')
        agg_dict = {'clicks': 'sum', 'impressions': 'sum'}
        if 'query' in df_period.columns:
            df_period['is_marque'] = df_period['query'].apply(lambda x: is_marque_query(x, regex_pattern))
            marque_agg = df_period[df_period['is_marque']].groupby('month_period').agg(agg_dict).rename(columns={'clicks': 'clics_marque', 'impressions': 'impressions_marque'})
            hors_marque_agg = df_period[~df_period['is_marque']].groupby('month_period').agg(agg_dict).rename(columns={'clicks': 'clics_hors_marque', 'impressions': 'impressions_hors_marque'})
            total_agg = df_period.groupby('month_period').agg(agg_dict).rename(columns={'clicks': 'total_clics', 'impressions': 'total_impressions'})
            final = total_agg.join(marque_agg, how='outer').join(hors_marque_agg, how='outer')
        else:
            final = df_period.groupby('month_period').agg(agg_dict).rename(columns={'clicks': 'total_clics', 'impressions': 'total_impressions'})
        return final.fillna(0)

    df_main = _df_pages if _df_pages is not None else _df_queries
    monthly_n = aggregate_monthly(df_main, periode_n_dates[0], periode_n_dates[1])
    monthly_n1 = aggregate_monthly(df_main, periode_n1_dates[0], periode_n1_dates[1])
    if monthly_n.empty or monthly_n1.empty: return pd.DataFrame()

    monthly_n['month_name'] = monthly_n.index.strftime('%b')
    monthly_n['month_sorter'] = monthly_n.index.month
    monthly_n1['month_name'] = monthly_n1.index.strftime('%b')
    final_df = pd.merge(monthly_n, monthly_n1, on='month_name', how='inner', suffixes=('_n', '_n1'))
    final_df = final_df.rename(columns={'total_clics_n': 'total_clics', 'impressions_n': 'impressions', 'clics_marque_n': 'clics_marque', 'impressions_marque_n': 'impressions_marque', 'clics_hors_marque_n': 'clics_hors_marque'})
    final_df = final_df.rename(columns={'month_name': 'month_label'})
    final_df = final_df.sort_values('month_sorter').drop(columns=['month_sorter'])
    return final_df.fillna(0)

# --- Fonctions de Création de Graphiques ---
def add_evolution_arrow(fig, x_pos, y1, y2, color):
    if y1 > 0:
        evo_pct = ((y2 - y1) / y1) * 100
        fig.add_annotation(x=x_pos, y=max(y1, y2) + (max(y1, y2) * 0.1), text=f"<b>{evo_pct:+.1f}%</b>", showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor=color, ax=0, ay=-30, font=dict(color=color, size=12))

def create_evolution_chart(metrics, chart_title, labels, colors, style_options, axis_titles):
    """Create a bar chart showing evolution percentages for different metrics"""
    
    # Calculate evolution percentages
    evolutions = {}
    metric_pairs = [
        ('total_clics_n1', 'total_clics_n', 'total_clicks'),
        ('clics_marque_n1', 'clics_marque_n', 'brand_clicks'),
        ('clics_hors_marque_n1', 'clics_hors_marque_n', 'non_brand_clicks'),
        ('total_impressions_n1', 'total_impressions_n', 'total_impressions')
    ]
    
    for n1_key, n_key, label_key in metric_pairs:
        val_n1 = metrics.get(n1_key, 0)
        val_n = metrics.get(n_key, 0)
        if val_n1 > 0:
            evolution_pct = ((val_n - val_n1) / val_n1) * 100
        else:
            evolution_pct = 0 if val_n == 0 else 100
        evolutions[label_key] = evolution_pct
    
    # Prepare data for chart
    x_labels = [labels.get(key, key) for key in evolutions.keys()]
    y_values = list(evolutions.values())
    bar_colors = [colors['positive'] if val >= 0 else colors['negative'] for val in y_values]
    
    # Create figure
    fig = go.Figure(data=[
        go.Bar(
            x=x_labels,
            y=y_values,
            marker_color=bar_colors,
            text=[f"{val:+.1f}%" for val in y_values],
            textposition='auto',
            textfont=dict(size=style_options['bar_text_font_size'], color='white')
        )
    ])
    
    # Update layout
    fig.update_layout(
        title=chart_title,
        xaxis_title=axis_titles['x'],
        yaxis_title=axis_titles['y'],
        font=dict(family=style_options['font_family'], size=style_options['axis_font_size']),
        title_font_size=style_options['title_font_size'],
        height=500,
        showlegend=False,
        plot_bgcolor='white',
        yaxis=dict(ticksuffix='%')
    )
    
    return fig

def create_pie_charts(metrics, base_title, colors, style_options, labels, legends):
    """Create two pie charts showing brand vs non-brand distribution for both periods"""
    
    # Data for period N
    clics_marque_n = metrics.get('clics_marque_n', 0)
    clics_hors_marque_n = metrics.get('clics_hors_marque_n', 0)
    total_n = clics_marque_n + clics_hors_marque_n
    
    # Data for period N-1
    clics_marque_n1 = metrics.get('clics_marque_n1', 0)
    clics_hors_marque_n1 = metrics.get('clics_hors_marque_n1', 0)
    total_n1 = clics_marque_n1 + clics_hors_marque_n1
    
    # Create pie chart for period N
    if total_n > 0:
        fig_n = go.Figure(data=[
            go.Pie(
                labels=[labels['brand'], labels['non_brand']],
                values=[clics_marque_n, clics_hors_marque_n],
                marker_colors=[colors['marque'], colors['hors_marque']],
                textinfo='label+percent+value',
                textfont=dict(size=style_options['axis_font_size'])
            )
        ])
        
        fig_n.update_layout(
            title=f"{base_title} - {legends['n']}<br>{metrics['nom_periode_n']}",
            font=dict(family=style_options['font_family']),
            title_font_size=style_options['title_font_size'],
            height=400
        )
    else:
        # Empty pie chart for period N
        fig_n = go.Figure()
        fig_n.update_layout(
            title=f"{base_title} - {legends['n']}<br>Aucune donnée",
            font=dict(family=style_options['font_family']),
            title_font_size=style_options['title_font_size'],
            height=400
        )
    
    # Create pie chart for period N-1
    if total_n1 > 0:
        fig_n1 = go.Figure(data=[
            go.Pie(
                labels=[labels['brand'], labels['non_brand']],
                values=[clics_marque_n1, clics_hors_marque_n1],
                marker_colors=[colors['marque'], colors['hors_marque']],
                textinfo='label+percent+value',
                textfont=dict(size=style_options['axis_font_size'])
            )
        ])
        
        fig_n1.update_layout(
            title=f"{base_title} - {legends['n1']}<br>{metrics['nom_periode_n1']}",
            font=dict(family=style_options['font_family']),
            title_font_size=style_options['title_font_size'],
            height=400
        )
    else:
        # Empty pie chart for period N-1
        fig_n1 = go.Figure()
        fig_n1.update_layout(
            title=f"{base_title} - {legends['n1']}<br>Aucune donnée",
            font=dict(family=style_options['font_family']),
            title_font_size=style_options['title_font_size'],
            height=400
        )
    
    return fig_n, fig_n1

def create_generic_bar_chart(metrics, config, chart_title, color, style_options, axis_titles, legends, show_arrows):
    val_n1, val_n = metrics.get(config['metric_n1'], 0), metrics.get(config['metric_n'], 0)
    fig = go.Figure(data=[go.Bar(x=[f"{legends['n1']}<br>{metrics['nom_periode_n1']}", f"{legends['n']}<br>{metrics['nom_periode_n']}"], y=[val_n1, val_n], marker_color=color, text=[f"{val_n1:,}", f"{val_n:,}"], textposition='auto', textfont=dict(size=style_options['bar_text_font_size'], color='white'))])
    if show_arrows and val_n1 > 0:
        color_evo = DEFAULT_COLORS['evolution_positive'] if val_n >= val_n1 else DEFAULT_COLORS['evolution_negative']
        add_evolution_arrow(fig, 0.5, val_n1, val_n, color_evo)
    fig.update_layout(title=chart_title, xaxis_title=axis_titles['x'], yaxis_title=axis_titles['y'], font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, showlegend=False, plot_bgcolor='white')
    return fig

def create_monthly_breakdown_chart(df, config, chart_title, legends, colors, style_options, axis_titles, show_arrows, custom_x_labels=None):
    x_axis_labels = custom_x_labels if custom_x_labels is not None else df['month_label']
    y_n, y_n1 = df[config['metric_n']], df[config['metric_n1']]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x_axis_labels, y=y_n1, name=legends['n1'], marker_color=colors['n1'], text=[f"{v:,.0f}" for v in y_n1], textposition='outside'))
    fig.add_trace(go.Bar(x=x_axis_labels, y=y_n, name=legends['n'], marker_color=colors['n'], text=[f"{v:,.0f}" for v in y_n], textposition='outside'))
    if show_arrows:
        for i, month in enumerate(x_axis_labels):
            val_n, val_n1 = y_n.iloc[i], y_n1.iloc[i]
            if val_n1 > 0:
                color_evo = DEFAULT_COLORS['evolution_positive'] if val_n >= val_n1 else DEFAULT_COLORS['evolution_negative']
                add_evolution_arrow(fig, month, val_n1, val_n, color_evo)
    fig.update_layout(title=chart_title, xaxis_title=axis_titles['x'], yaxis_title=axis_titles['y'], barmode='group', font=dict(family=style_options['font_family'], size=style_options['axis_font_size']), title_font_size=style_options['title_font_size'], height=500, plot_bgcolor='white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# --- Application Principale ---
def main():
    st.title("📊 Dashboard SEO - Générateur de Graphiques")
    st.markdown("**Analysez vos performances SEO en comparant des périodes.**")
    st.markdown("---"); st.markdown("### 🏷️ Configuration"); regex_pattern = st.text_input("Regex Marque")
    try: re.compile(regex_pattern)
    except re.error: st.error("❌ Regex invalide."); st.stop()
    st.markdown("---"); st.markdown("### 📥 Import des Données GSC")
    col1, col2 = st.columns(2)
    uploaded_file_queries = col1.file_uploader("1. Fichier 'Requêtes' (Obligatoire, Excel ou CSV)", type=['xlsx', 'xls', 'csv'])
    uploaded_file_pages = col2.file_uploader("2. Fichier 'Pages' (Optionnel, Excel ou CSV)", type=['xlsx', 'xls', 'csv'])

    if uploaded_file_queries:
        df_queries = load_data(uploaded_file_queries)
        st.success(f"✅ Fichier 'Requêtes' chargé ({len(df_queries):,} lignes).")
        if 'query' not in df_queries.columns:
            st.error("ERREUR CRITIQUE : La colonne 'query' est absente du fichier 'Requêtes'.")
            st.warning(f"Les colonnes détectées sont : {df_queries.columns.tolist()}"); st.warning("Veuillez vérifier que vous avez chargé le bon fichier dans la bonne case."); st.stop()

        df_pages = None
        if uploaded_file_pages: df_pages = load_data(uploaded_file_pages); st.success(f"✅ Fichier 'Pages' chargé ({len(df_pages):,} lignes).")
        else: st.warning("⚠️ Fichier 'Pages' non fourni. Les totaux seront basés sur les données 'Requêtes'.")
        
        today = datetime.now().date(); anchor_date = today.replace(day=1) - timedelta(days=1)
        st.info(f"💡 L'analyse par défaut se base sur les mois terminés. Date de référence: **{anchor_date.strftime('%d/%m/%Y')}**.")
        st.markdown("### 📅 Type de Comparaison"); comparison_mode = st.radio("Mode :", ["Périodes Consécutives", "Année sur Année (YoY)"], horizontal=True, key="comparison_mode")
        
        period_type, use_monthly_view = "Personnalisé", False

        if comparison_mode == "Périodes Consécutives":
            options = ["3 derniers mois complets", "6 derniers mois complets", "Dernier mois complet", "Période Personnalisée"]
            selection = st.radio("Période :", options, horizontal=True, key="consecutive_period")
            if selection == "Période Personnalisée":
                st.write("##### Sélection Période N"); c1, c2 = st.columns(2); n_start = c1.date_input("Date de début (N)", value=anchor_date - timedelta(days=89), key="cust_n_start"); n_end = c2.date_input("Date de fin (N)", value=anchor_date, key="cust_n_end")
                st.write("##### Sélection Période N-1"); c3, c4 = st.columns(2); n1_start = c3.date_input("Date de début (N-1)", value=n_start - timedelta(days=(n_end-n_start).days + 1), key="cust_n1_start"); n1_end = c4.date_input("Date de fin (N-1)", value=n_start - timedelta(days=1), key="cust_n1_end")
            else:
                months = {"3 derniers mois complets": 3, "6 derniers mois complets": 6, "Dernier mois complet": 1}[selection]
                n_end = anchor_date; n_start = get_start_of_month(anchor_date, months - 1)
                n1_end = n_start - timedelta(days=1); n1_start = get_start_of_month(n1_end, months - 1); period_type = f"{selection} vs Précédent"
        else:
            options_yoy = ["3 derniers mois complets", "Période Personnalisée"]
            selection_yoy = st.radio("Période (YoY) :", options_yoy, horizontal=True, key="yoy_period")
            use_monthly_view = st.checkbox("Afficher la vue détaillée mois par mois", value=True, key="yoy_view_toggle")
            if selection_yoy == "Période Personnalisée":
                st.write("##### Sélection Période N"); c1, c2 = st.columns(2); n_start = c1.date_input("Date de début (N)", value=anchor_date - timedelta(days=89), key="cust_yoy_n_start"); n_end = c2.date_input("Date de fin (N)", value=anchor_date, key="cust_yoy_n_end")
                st.write("##### Sélection Période N-1 (YoY)"); c3, c4 = st.columns(2); n1_start = c3.date_input("Date de début (N-1)", value=n_start.replace(year=n_start.year - 1), key="cust_yoy_n1_start"); n1_end = c4.date_input("Date de fin (N-1)", value=n_end.replace(year=n_end.year - 1), key="cust_yoy_n1_end")
            else:
                n_end = anchor_date; n_start = get_start_of_month(anchor_date, 2)
                n1_start = n_start.replace(year=n_start.year - 1); n1_end = n_end.replace(year=n_end.year - 1); period_type = "3 derniers mois vs N-1 (YoY)"
        
        show_evolution_arrows = st.checkbox("Afficher les pourcentages d'évolution sur les graphiques", value=True)

        if n_start > n_end or n1_start > n1_end: st.error("La date de début ne peut pas être après la date de fin."); st.stop()
        
        periode_n_dates, periode_n1_dates = (n_start, n_end), (n1_start, n1_end)
        metrics = process_data_for_periods(df_queries, df_pages, periode_n_dates, periode_n1_dates, regex_pattern)
            
        if not metrics: st.stop()
        if metrics['total_clics_n'] == 0 and metrics['total_clics_n1'] == 0: st.warning("⚠️ Aucune donnée trouvée pour les périodes sélectionnées.")
        else:
            st.markdown("---"); st.markdown("### 📈 Analyse")
            if comparison_mode == "Année sur Année (YoY)" and use_monthly_view:
                st.markdown("#### Vue Détaillée Mois par Mois")
                monthly_data = get_monthly_breakdown(df_queries, df_pages, periode_n_dates, periode_n1_dates, regex_pattern)
                if not monthly_data.empty:
                    year_n, year_n1 = periode_n_dates[0].year, periode_n1_dates[0].year
                    with st.expander("✏️ Personnaliser les étiquettes des mois"):
                        editable_labels = monthly_data['month_label'].tolist()
                        if editable_labels:
                            cols = st.columns(len(editable_labels)); 
                            for i, label in enumerate(editable_labels): editable_labels[i] = cols[i].text_input(f"Mois {i+1}", label, key=f"month_label_{i}")
                    monthly_chart_configs = {"global": {"title_key": "global_clicks", "metric_n": "total_clics", "metric_n1": "total_clics_n1"},"marque": {"title_key": "brand_clicks", "metric_n": "clics_marque", "metric_n1": "clics_marque_n1"},"hors_marque": {"title_key": "non_brand_clicks", "metric_n": "clics_hors_marque", "metric_n1": "clics_hors_marque_n1"},"impressions": {"title_key": "brand_impressions", "metric_n": "impressions", "metric_n1": "impressions_n1"}}
                    for key, config in monthly_chart_configs.items():
                        if config['metric_n'] in monthly_data.columns and config['metric_n1'] in monthly_data.columns:
                            with st.container(border=True):
                                with st.expander(f"✏️ Personnaliser : {DEFAULT_TITLES[config['title_key']]} (Mensuel)"):
                                    c1,c2,c3=st.columns([2,1,1]); chart_title_monthly=c1.text_input("Titre",f"{DEFAULT_TITLES[config['title_key']]} ({DEFAULT_TITLES['monthly_evolution']})",key=f"monthly_title_{key}"); axis_titles_monthly={'x':c2.text_input("Axe X",DEFAULT_TITLES['axis_month'],key=f"monthly_axis_x_{key}"),'y':c3.text_input("Axe Y",DEFAULT_TITLES.get(f"axis_{key}",'Valeur'),key=f"monthly_axis_y_{key}")}; legends_monthly={'n':c2.text_input("Légende N",f"Année {year_n}",key=f"monthly_leg_n_{key}"),'n1':c3.text_input("Légende N-1",f"Année {year_n1}",key=f"monthly_leg_n1_{key}")}; c1,c2=st.columns(2); colors_monthly={'n':c1.color_picker("Couleur N",DEFAULT_COLORS.get(f"{key}_seo",DEFAULT_COLORS['global_seo']),key=f"monthly_color_n_{key}"),'n1':c2.color_picker("Couleur N-1",DEFAULT_COLORS['secondary_light'],key=f"monthly_color_n1_{key}")}; style_options_monthly={'font_family':st.selectbox("Police",['Arial','Verdana'],index=0,key=f"monthly_font_{key}"),'title_font_size':st.slider("Taille Titre",10,30,18,key=f"monthly_font_title_{key}"),'axis_font_size':st.slider("Taille Axes",8,20,12,key=f"monthly_font_axis_{key}"),'bar_text_font_size':12}
                                fig_monthly = create_monthly_breakdown_chart(monthly_data, config, chart_title_monthly, legends_monthly, colors_monthly, style_options_monthly, axis_titles_monthly, show_evolution_arrows, custom_x_labels=editable_labels)
                                st.plotly_chart(fig_monthly, use_container_width=True)
                else: st.warning("Aucune donnée mensuelle comparable n'a été trouvée pour la vue détaillée.")
            else:
                st.markdown("#### Vue Agrégée sur la Période")
                with st.container(border=True):
                    with st.expander("✏️ Personnaliser : Synthèse des Évolutions"):
                        c1,c2,c3=st.columns([2,1,1]); chart_title_evo=c1.text_input("Titre",f"{DEFAULT_TITLES['evolution_summary']} - {period_type}",key="evo_title"); axis_titles_evo={'x':c2.text_input("Axe X",DEFAULT_TITLES['axis_metric'],key="evo_axis_x"),'y':c3.text_input("Axe Y",DEFAULT_TITLES['axis_evolution'],key="evo_axis_y")}; labels_evo={'total_clicks':st.text_input("Label Clics Totaux",DEFAULT_TITLES['metric_total_clicks'],key="evo_label_tc"),'brand_clicks':st.text_input("Label Clics Marque",DEFAULT_TITLES['metric_brand_clicks'],key="evo_label_bc"),'non_brand_clicks':st.text_input("Label Clics Hors-Marque",DEFAULT_TITLES['metric_non_brand_clicks'],key="evo_label_nbc"),'total_impressions':st.text_input("Label Impressions",DEFAULT_TITLES['metric_total_impressions'],key="evo_label_ti")}; c1,c2=st.columns(2); colors_evo={'positive':c1.color_picker("Évo Positive",DEFAULT_COLORS['evolution_positive'],key="evo_color_pos"),'negative':c2.color_picker("Évo Négative",DEFAULT_COLORS['evolution_negative'],key="evo_color_neg")}; style_options_evo={'font_family':st.selectbox("Police",['Arial','Verdana'],index=0,key="evo_font"),'title_font_size':st.slider("Taille Titre",10,30,18,key="evo_font_title"),'axis_font_size':st.slider("Taille Axes",8,20,12,key="evo_font_axis"),'bar_text_font_size':st.slider("Taille Texte Barres",8,20,12,key="evo_font_bar")}
                    fig_evo = create_evolution_chart(metrics, chart_title_evo, labels_evo, colors_evo, style_options_evo, axis_titles_evo)
                    st.plotly_chart(fig_evo, use_container_width=True)
                chart_configs = {"global": {"title_key": "global_clicks", "metric_n": "total_clics_n", "metric_n1": "total_clics_n1"},"marque": {"title_key": "brand_clicks", "metric_n": "clics_marque_n", "metric_n1": "clics_marque_n1"},"hors_marque": {"title_key": "non_brand_clicks", "metric_n": "clics_hors_marque_n", "metric_n1": "clics_hors_marque_n1"}}
                for key, config in chart_configs.items():
                    with st.container(border=True):
                        with st.expander(f"✏️ Personnaliser : {DEFAULT_TITLES[config['title_key']]}"):
                            c1,c2,c3=st.columns([2,1,1]); chart_title_bar=c1.text_input("Titre",f"{DEFAULT_TITLES[config['title_key']]} ({DEFAULT_TITLES['axis_clicks']}) - {period_type}",key=f"bar_title_{key}"); axis_titles_bar={'x':c2.text_input("Axe X",DEFAULT_TITLES['axis_period'],key=f"bar_axis_x_{key}"),'y':c3.text_input("Axe Y",DEFAULT_TITLES['axis_clicks'],key=f"bar_axis_y_{key}")}; legends_bar={'n':c2.text_input("Légende N",DEFAULT_TITLES['legend_n'],key=f"bar_leg_n_{key}"),'n1':c3.text_input("Légende N-1",DEFAULT_TITLES['legend_n1'],key=f"bar_leg_n1_{key}")}; color_bar=st.color_picker("Couleur Barres",DEFAULT_COLORS.get(f"{key}_seo",DEFAULT_COLORS['global_seo']),key=f"bar_color_{key}"); style_options_bar={'font_family':st.selectbox("Police",['Arial','Verdana'],index=0,key=f"bar_font_{key}"),'title_font_size':st.slider("Taille Titre",10,30,18,key=f"bar_font_title_{key}"),'axis_font_size':st.slider("Taille Axes",8,20,12,key=f"bar_font_axis_{key}"),'bar_text_font_size':st.slider("Taille Texte Barres",8,20,12,key=f"bar_font_text_{key}")}
                        fig_bar = create_generic_bar_chart(metrics, config, chart_title_bar, color_bar, style_options_bar, axis_titles_bar, legends_bar, show_evolution_arrows)
                        st.plotly_chart(fig_bar, use_container_width=True)

            with st.container(border=True):
                with st.expander("✏️ Personnaliser : Répartition des Clics"):
                    base_title_pie=st.text_input("Titre de base",DEFAULT_TITLES['pie_chart'],key="pie_title");c1,c2=st.columns(2);labels_pie={'brand':c1.text_input("Label 'Marque'",DEFAULT_TITLES['pie_label_brand'],key="pie_label_b"),'non_brand':c2.text_input("Label 'Hors-Marque'",DEFAULT_TITLES['pie_label_non_brand'],key="pie_label_nb")};legends_pie={'n':c1.text_input("Légende N",DEFAULT_TITLES['legend_n'],key="pie_leg_n"),'n1':c2.text_input("Légende N-1",DEFAULT_TITLES['legend_n1'],key="pie_leg_n1")};c1,c2=st.columns(2);colors_pie={'marque':c1.color_picker("Couleur Marque",DEFAULT_COLORS['pie_marque'],key="pie_color_brand"),'hors_marque':c2.color_picker("Couleur Hors-Marque",DEFAULT_COLORS['pie_hors_marque'],key="pie_color_nonbrand")};style_options_pie={'font_family':st.selectbox("Police",['Arial','Verdana'],index=0,key="pie_font"),'title_font_size':st.slider("Taille Titre",10,30,18,key="pie_font_title"),'axis_font_size':st.slider("Taille Texte",8,20,12,key="pie_font_text")}
                pie1, pie2 = create_pie_charts(metrics, base_title_pie, colors_pie, style_options_pie, labels_pie, legends_pie)
                col1, col2 = st.columns(2); col1.plotly_chart(pie1, use_container_width=True); col2.plotly_chart(pie2, use_container_width=True)

if __name__ == "__main__":
    main()
