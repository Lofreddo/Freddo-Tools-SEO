# scripts/SeoChecker.py

import streamlit as st
import sqlite3
import pandas as pd
import os

def main():
    st.title("Analyse SEO Technique avec Screaming Frog")

    # Uploader pour le fichier .dbseospider
    uploaded_file = st.file_uploader("Téléchargez votre fichier .dbseospider", type="dbseospider")

    if uploaded_file is not None:
        # Enregistrer le fichier uploadé dans un fichier temporaire
        temp_file_path = 'temp.dbseospider'
        with open(temp_file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        # Se connecter à la base de données SQLite
        conn = sqlite3.connect(temp_file_path)

        # Liste des critères avec leur fonction de vérification
        criteria_list = [
            {"criterion": "Vérifier le robots.txt (Règles, Sitemap présent)", "function": check_robots_txt},
            {"criterion": "Vérifier le Sitemap (Pages non indexables / Orphelines)", "function": check_sitemap},
            {"criterion": "Présence de sous-domaines", "function": check_subdomains},
            {"criterion": "Liens vers pages 404 / 301", "function": check_links_to_404_301},
            {"criterion": "Pages non indexables crawlées", "function": check_non_indexable_pages_crawled},
            {"criterion": "Erreurs 500", "function": check_500_errors},
            {"criterion": "Redirection http > https", "function": check_http_to_https_redirection},
            {"criterion": "Redirection www > sans www (ou inverse)", "function": check_www_redirection},
            {"criterion": "Redirection avec '/' > sans '/' (ou inverse)", "function": check_trailing_slash_redirection},
            {"criterion": "Soft 404", "function": check_soft_404},
            {"criterion": "Présence de redirections Meta Refresh", "function": check_meta_refresh_redirects},
            {"criterion": "Chaînes de redirections", "function": check_redirect_chains},
            {"criterion": "Redirections 301 vers URLs en 404", "function": check_301_to_404},
            {"criterion": "Poids des images (> 100 ko)", "function": check_image_sizes},
            {"criterion": "Balises Alt présentes pour chaque image", "function": check_alt_tags_presence},
            {"criterion": "Attributs width= & height= dans les images", "function": check_image_dimensions_attributes},
            {"criterion": "Format des images (jpeg / WebP)", "function": check_image_formats},
            {"criterion": "Balises Titles et H1 uniques", "function": check_unique_titles_h1},
            {"criterion": "Longueur des balises title", "function": check_title_length},
            {"criterion": "Vérification de l'indexabilité des pages", "function": check_pages_indexability},
            {"criterion": "Présence de hreflang", "function": check_hreflang},
            {"criterion": "Balise X-default présente", "function": check_x_default},
            {"criterion": "Langue dans la balise <html>", "function": check_html_lang_attribute},
            {"criterion": "Utilisation de balises HTML5", "function": check_html5_usage},
            {"criterion": "Présence de la balise viewport", "function": check_viewport_meta},
            {"criterion": "Certificat SSL présent et sécurisé", "function": check_ssl_certificate},
            {"criterion": "Vérifier la gestion du multilingue (TLD / Dossier / Sous-domaine)", "function": check_multilingual_handling},
            {"criterion": "Vérification de l'optimisation du moteur de recherche interne", "function": check_internal_search_optimization},
            {"criterion": "Lazy Loading des images", "function": check_lazy_loading},
            {"criterion": "Liens internes contenant des UTM", "function": check_internal_links_with_utm},
            {"criterion": "Structure Hn (Ordre, Hn Structurel, Hn Vides)", "function": check_hn_structure},
            {"criterion": "Vitesse de chargement du site", "function": check_page_speed},
            {"criterion": "Utilisation d'un CDN", "function": check_cdn_usage},
            {"criterion": "Taille des pages inférieures à 4Mo", "function": check_page_size},
            {"criterion": "Présence de scripts inutilisés dans le code source", "function": check_unused_scripts},
            {"criterion": "Cache navigateur activé", "function": check_browser_cache},
            {"criterion": "Présence de CSS dans le code HTML", "function": check_inline_css},
            {"criterion": "Score Optimisation Pagespeed", "function": check_pagespeed_score},
            {"criterion": "Utilisation de DNS Prefetching", "function": check_dns_prefetching},
            {"criterion": "Serveur mutualisé ou dédié", "function": check_server_type}
        ]

        results = []
        for item in criteria_list:
            criterion = item["criterion"]
            function = item["function"]
            status = function(conn)
            results.append({"Critère": criterion, "Statut": status})

        # Fermer la connexion
        conn.close()

        # Supprimer le fichier temporaire
        os.remove(temp_file_path)

        # Créer un DataFrame des résultats
        df_results = pd.DataFrame(results)

        # Afficher les résultats dans l'application Streamlit
        st.header("Résultats de l'analyse")
        st.table(df_results)

        # Enregistrer dans un fichier Excel
        output_file = "resultats_analyse_seo.xlsx"
        df_results.to_excel(output_file, index=False)

        # Proposer le téléchargement du fichier
        with open(output_file, "rb") as f:
            st.download_button(
                label="Télécharger le rapport d'analyse",
                data=f,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Supprimer le fichier de résultats après le téléchargement
        os.remove(output_file)

    else:
        st.info("Veuillez télécharger un fichier .dbseospider pour commencer l'analyse.")


# Fonctions de vérification pour chaque critère

def check_robots_txt(conn):
    try:
        df_robots = pd.read_sql_query("SELECT * FROM RobotsTxt", conn)
        if not df_robots.empty:
            robots_content = df_robots['Content'].iloc[0]
            sitemap_present = "Sitemap:" in robots_content
            return "Sitemap présent dans robots.txt" if sitemap_present else "Sitemap non présent dans robots.txt"
        else:
            return "robots.txt non trouvé"
    except Exception as e:
        return f"Erreur lors de la vérification du robots.txt : {e}"

def check_sitemap(conn):
    try:
        df_sitemap = pd.read_sql_query("SELECT * FROM Sitemaps", conn)
        df_internal = pd.read_sql_query("SELECT Address FROM Internal WHERE Indexability = 'Indexable'", conn)

        sitemap_urls = df_sitemap['Address'].tolist()
        internal_urls = df_internal['Address'].tolist()

        non_indexable_in_sitemap = df_internal[(df_internal['Address'].isin(sitemap_urls)) & (df_internal['Indexability'] != 'Indexable')]
        orphan_pages = set(sitemap_urls) - set(internal_urls)

        status = ""
        if not non_indexable_in_sitemap.empty:
            status += f"{len(non_indexable_in_sitemap)} pages non indexables dans le sitemap. "
        else:
            status += "Aucune page non indexable dans le sitemap. "

        if orphan_pages:
            status += f"{len(orphan_pages)} pages orphelines détectées."
        else:
            status += "Aucune page orpheline détectée."

        return status

    except Exception as e:
        return f"Erreur lors de la vérification du sitemap : {e}"

def check_subdomains(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address FROM Internal", conn)
        domains = df_internal['Address'].apply(lambda x: x.split('/')[2])
        main_domain = domains.mode()[0]
        subdomains = domains[domains != main_domain].unique()

        if len(subdomains) > 0:
            return f"Présence de sous-domaines : {', '.join(subdomains)}"
        else:
            return "Aucun sous-domaine détecté"
    except Exception as e:
        return f"Erreur lors de la vérification des sous-domaines : {e}"

def check_links_to_404_301(conn):
    try:
        df_links = pd.read_sql_query("SELECT Source, Destination FROM AllOutlinks", conn)
        df_status = pd.read_sql_query("SELECT Address, StatusCode FROM Internal", conn)

        df_merged = df_links.merge(df_status, left_on='Destination', right_on='Address', how='left')
        errors = df_merged[df_merged['StatusCode'].isin([404, 301])]

        if not errors.empty:
            counts = errors['StatusCode'].value_counts().to_dict()
            return f"Liens vers pages : {counts}"
        else:
            return "Aucun lien vers pages 404 ou 301"
    except Exception as e:
        return f"Erreur lors de la vérification des liens : {e}"

def check_non_indexable_pages_crawled(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, Indexability FROM Internal", conn)
        non_indexable = df_internal[df_internal['Indexability'] != 'Indexable']

        if not non_indexable.empty:
            return f"{len(non_indexable)} pages non indexables crawlées"
        else:
            return "Aucune page non indexable crawlée"
    except Exception as e:
        return f"Erreur lors de la vérification des pages non indexables : {e}"

def check_500_errors(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, StatusCode FROM Internal", conn)
        errors_500 = df_internal[df_internal['StatusCode'] == 500]

        if not errors_500.empty:
            return f"{len(errors_500)} erreurs 500 détectées"
        else:
            return "Aucune erreur 500 détectée"
    except Exception as e:
        return f"Erreur lors de la vérification des erreurs 500 : {e}"

def check_http_to_https_redirection(conn):
    try:
        df_redirects = pd.read_sql_query("SELECT Address, RedirectURI FROM Internal WHERE RedirectURI IS NOT NULL", conn)
        redirects_http_to_https = df_redirects[df_redirects['Address'].str.startswith('http://') & df_redirects['RedirectURI'].str.startswith('https://')]

        if not redirects_http_to_https.empty:
            return f"{len(redirects_http_to_https)} redirections de http vers https détectées"
        else:
            return "Aucune redirection de http vers https détectée"
    except Exception as e:
        return f"Erreur lors de la vérification des redirections http > https : {e}"

def check_www_redirection(conn):
    try:
        df_redirects = pd.read_sql_query("SELECT Address, RedirectURI FROM Internal WHERE RedirectURI IS NOT NULL", conn)
        redirects = df_redirects[
            (df_redirects['Address'].str.contains('//www.')) & (~df_redirects['RedirectURI'].str.contains('//www.')) |
            (~df_redirects['Address'].str.contains('//www.')) & (df_redirects['RedirectURI'].str.contains('//www.'))
        ]

        if not redirects.empty:
            return f"{len(redirects)} redirections www vers sans www ou inverse détectées"
        else:
            return "Aucune redirection www vers sans www ou inverse détectée"
    except Exception as e:
        return f"Erreur lors de la vérification des redirections www : {e}"

def check_trailing_slash_redirection(conn):
    try:
        df_redirects = pd.read_sql_query("SELECT Address, RedirectURI FROM Internal WHERE RedirectURI IS NOT NULL", conn)
        redirects = df_redirects[
            (df_redirects['Address'].str.endswith('/')) & (~df_redirects['RedirectURI'].str.endswith('/')) |
            (~df_redirects['Address'].str.endswith('/')) & (df_redirects['RedirectURI'].str.endswith('/'))
        ]

        if not redirects.empty:
            return f"{len(redirects)} redirections avec '/' vers sans '/' ou inverse détectées"
        else:
            return "Aucune redirection avec '/' vers sans '/' ou inverse détectée"
    except Exception as e:
        return f"Erreur lors de la vérification des redirections avec '/' : {e}"

def check_soft_404(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, StatusCode, Status FROM Internal", conn)
        soft_404 = df_internal[df_internal['Status'] == 'Soft 404']

        if not soft_404.empty:
            return f"{len(soft_404)} pages soft 404 détectées"
        else:
            return "Aucune page soft 404 détectée"
    except Exception as e:
        return f"Erreur lors de la vérification des soft 404 : {e}"

def check_meta_refresh_redirects(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, MetaRefresh FROM Internal", conn)
        meta_refresh_redirects = df_internal[df_internal['MetaRefresh'].notnull() & df_internal['MetaRefresh'] != '']

        if not meta_refresh_redirects.empty:
            return f"{len(meta_refresh_redirects)} redirections Meta Refresh détectées"
        else:
            return "Aucune redirection Meta Refresh détectée"
    except Exception as e:
        return f"Erreur lors de la vérification des redirections Meta Refresh : {e}"

def check_redirect_chains(conn):
    try:
        df_redirect_chains = pd.read_sql_query("SELECT * FROM RedirectChains", conn)

        if not df_redirect_chains.empty:
            return f"{len(df_redirect_chains)} chaînes de redirections détectées"
        else:
            return "Aucune chaîne de redirection détectée"
    except Exception as e:
        return f"Erreur lors de la vérification des chaînes de redirections : {e}"

def check_301_to_404(conn):
    try:
        df_redirects = pd.read_sql_query("SELECT Address, RedirectURI, StatusCode FROM Internal WHERE StatusCode = 301", conn)
        df_status = pd.read_sql_query("SELECT Address, StatusCode FROM Internal", conn)

        df_merged = df_redirects.merge(df_status, left_on='RedirectURI', right_on='Address', how='left', suffixes=('', '_Redirected'))
        redirects_to_404 = df_merged[df_merged['StatusCode_Redirected'] == 404]

        if not redirects_to_404.empty:
            return f"{len(redirects_to_404)} redirections 301 vers URLs en 404 détectées"
        else:
            return "Aucune redirection 301 vers URLs en 404 détectée"
    except Exception as e:
        return f"Erreur lors de la vérification des redirections 301 vers 404 : {e}"

def check_image_sizes(conn):
    try:
        df_images = pd.read_sql_query("SELECT Address, Size FROM Images", conn)
        large_images = df_images[df_images['Size'] > 100 * 1024]  # 100 ko

        if not large_images.empty:
            return f"{len(large_images)} images dépassant 100 ko"
        else:
            return "Toutes les images sont inférieures à 100 ko"
    except Exception as e:
        return f"Erreur lors de la vérification des tailles d'images : {e}"

def check_alt_tags_presence(conn):
    try:
        df_images = pd.read_sql_query("SELECT Address, AltText FROM Images", conn)
        images_without_alt = df_images[df_images['AltText'].isnull() | (df_images['AltText'] == '')]

        if not images_without_alt.empty:
            return f"{len(images_without_alt)} images sans balise alt"
        else:
            return "Toutes les images ont une balise alt"
    except Exception as e:
        return f"Erreur lors de la vérification des balises alt : {e}"

def check_image_dimensions_attributes(conn):
    try:
        df_images = pd.read_sql_query("SELECT Address, Width, Height FROM Images", conn)
        images_without_dimensions = df_images[(df_images['Width'] == 0) | (df_images['Height'] == 0)]

        if not images_without_dimensions.empty:
            return f"{len(images_without_dimensions)} images sans attributs width ou height"
        else:
            return "Toutes les images ont des attributs width et height"
    except Exception as e:
        return f"Erreur lors de la vérification des attributs width et height : {e}"

def check_image_formats(conn):
    try:
        df_images = pd.read_sql_query("SELECT Address FROM Images", conn)
        allowed_formats = ['.jpg', '.jpeg', '.png', '.webp']
        images_with_wrong_format = df_images[~df_images['Address'].str.lower().str.endswith(tuple(allowed_formats))]

        if not images_with_wrong_format.empty:
            return f"{len(images_with_wrong_format)} images avec un format non recommandé"
        else:
            return "Toutes les images sont au format recommandé (jpeg, png, webp)"
    except Exception as e:
        return f"Erreur lors de la vérification des formats d'images : {e}"

def check_unique_titles_h1(conn):
    try:
        df_titles = pd.read_sql_query("SELECT Address, Title1 FROM Internal", conn)
        df_h1 = pd.read_sql_query("SELECT Address, H1_1 FROM Internal", conn)

        duplicate_titles = df_titles[df_titles.duplicated(subset='Title1', keep=False)]
        duplicate_h1 = df_h1[df_h1.duplicated(subset='H1_1', keep=False)]

        status = ""
        if not duplicate_titles.empty:
            status += f"{len(duplicate_titles)} titres dupliqués. "
        else:
            status += "Titres uniques. "

        if not duplicate_h1.empty:
            status += f"{len(duplicate_h1)} H1 dupliqués."
        else:
            status += "H1 uniques."

        return status
    except Exception as e:
        return f"Erreur lors de la vérification des titres et H1 uniques : {e}"

def check_title_length(conn):
    try:
        df_titles = pd.read_sql_query("SELECT Address, Title1, Title1Length FROM Internal", conn)
        titles_too_long = df_titles[df_titles['Title1Length'] > 60]

        if not titles_too_long.empty:
            return f"{len(titles_too_long)} titres dépassant 60 caractères"
        else:
            return "Tous les titres ont une longueur adéquate"
    except Exception as e:
        return f"Erreur lors de la vérification de la longueur des titres : {e}"

def check_pages_indexability(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, Indexability, MetaRobots, MetaRobots_1_Directive FROM Internal", conn)
        non_indexable_pages = df_internal[df_internal['Indexability'] != 'Indexable']

        if not non_indexable_pages.empty:
            return f"{len(non_indexable_pages)} pages non indexables détectées"
        else:
            return "Toutes les pages sont indexables"
    except Exception as e:
        return f"Erreur lors de la vérification de l'indexabilité des pages : {e}"

def check_hreflang(conn):
    try:
        df_hreflang = pd.read_sql_query("SELECT * FROM Hreflang", conn)

        if not df_hreflang.empty:
            return "Balises hreflang présentes"
        else:
            return "Aucune balise hreflang détectée"
    except Exception as e:
        return f"Erreur lors de la vérification des hreflang : {e}"

def check_x_default(conn):
    try:
        df_hreflang = pd.read_sql_query("SELECT * FROM Hreflang", conn)
        x_default_present = df_hreflang['Lang'].str.lower().eq('x-default').any()

        if x_default_present:
            return "Balise x-default présente dans les hreflang"
        else:
            return "Aucune balise x-default détectée"
    except Exception as e:
        return f"Erreur lors de la vérification de la balise x-default : {e}"

def check_html_lang_attribute(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, HTMLLang FROM Internal", conn)
        pages_without_lang = df_internal[df_internal['HTMLLang'].isnull() | (df_internal['HTMLLang'] == '')]

        if not pages_without_lang.empty:
            return f"{len(pages_without_lang)} pages sans attribut lang dans <html>"
        else:
            return "Toutes les pages ont un attribut lang dans <html>"
    except Exception as e:
        return f"Erreur lors de la vérification de l'attribut lang dans <html> : {e}"

def check_html5_usage(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, DocType FROM Internal", conn)
        pages_with_html5 = df_internal[df_internal['DocType'].str.contains('html', case=False, na=False)]

        if len(pages_with_html5) == len(df_internal):
            return "Toutes les pages utilisent le doctype HTML5"
        else:
            return f"{len(df_internal) - len(pages_with_html5)} pages n'utilisent pas le doctype HTML5"
    except Exception as e:
        return f"Erreur lors de la vérification de l'utilisation de HTML5 : {e}"

def check_viewport_meta(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, MetaViewport FROM Internal", conn)
        pages_without_viewport = df_internal[df_internal['MetaViewport'].isnull() | (df_internal['MetaViewport'] == '')]

        if not pages_without_viewport.empty:
            return f"{len(pages_without_viewport)} pages sans balise meta viewport"
        else:
            return "Toutes les pages ont une balise meta viewport"
    except Exception as e:
        return f"Erreur lors de la vérification de la balise viewport : {e}"

def check_ssl_certificate(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, Protocol, Secure FROM Internal", conn)
        insecure_pages = df_internal[df_internal['Secure'] == 0]

        if not insecure_pages.empty:
            return f"{len(insecure_pages)} pages non sécurisées détectées"
        else:
            return "Toutes les pages sont sécurisées avec SSL"
    except Exception as e:
        return f"Erreur lors de la vérification du certificat SSL : {e}"

def check_multilingual_handling(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address FROM Internal", conn)
        if df_internal['Address'].str.contains('/fr/|/en/|/es/').any():
            return "Multilingue bien géré avec des sous-dossiers"
        else:
            return "Pas de gestion de multilingue via sous-dossiers"
    except Exception as e:
        return f"Erreur lors de la vérification du multilingue : {e}"

def check_internal_search_optimization(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address FROM Internal", conn)
        search_pages = df_internal[df_internal['Address'].str.contains('search')]
        if not search_pages.empty:
            return "Moteur de recherche interne détecté"
        else:
            return "Aucun moteur de recherche interne détecté"
    except Exception as e:
        return f"Erreur lors de la vérification du moteur de recherche interne : {e}"

def check_lazy_loading(conn):
    try:
        df_internal = pd.read_sql_query("SELECT Address, LazyLoaded FROM Images", conn)
        lazy_loaded_images = df_internal[df_internal['LazyLoaded'] == 'Yes']
        if not lazy_loaded_images.empty:
            return f"{len(lazy_loaded_images)} images avec lazy loading"
        else:
            return "Pas d'images avec lazy loading"
    except Exception as e:
        return f"Erreur lors de la vérification du lazy loading : {e}"

def check_internal_links_with_utm(conn):
    try:
        df_links = pd.read_sql_query("SELECT Address FROM AllOutlinks WHERE Address LIKE '%utm_%'", conn)
        if not df_links.empty:
            return f"{len(df_links)} liens internes avec des paramètres UTM détectés"
        else:
            return "Aucun lien interne avec des paramètres UTM"
    except Exception as e:
        return f"Erreur lors de la vérification des liens UTM : {e}"

def check_hn_structure(conn):
    try:
        df_hn = pd.read_sql_query("SELECT Address, H1_1, H2_1, H3_1 FROM Internal", conn)

        empty_hn = df_hn[(df_hn['H1_1'].isnull()) | (df_hn['H2_1'].isnull()) | (df_hn['H3_1'].isnull())]
        if not empty_hn.empty:
            return f"{len(empty_hn)} pages avec des balises Hn vides"
        else:
            return "Toutes les pages ont des balises Hn bien remplies"
    except Exception as e:
        return f"Erreur lors de la vérification des balises Hn : {e}"

def check_page_speed(conn):
    try:
        df_pages = pd.read_sql_query("SELECT Address, LoadTime FROM Internal", conn)
        slow_pages = df_pages[df_pages['LoadTime'] > 3000]  # Temps de chargement supérieur à 3 secondes
        if not slow_pages.empty:
            return f"{len(slow_pages)} pages avec un temps de chargement supérieur à 3 secondes"
        else:
            return "Toutes les pages ont un temps de chargement inférieur à 3 secondes"
    except Exception as e:
        return f"Erreur lors de la vérification du temps de chargement : {e}"

def check_cdn_usage(conn):
    try:
        df_resources = pd.read_sql_query("SELECT Address FROM Images UNION SELECT Address FROM CSS UNION SELECT Address FROM JS", conn)
        cdn_usage = df_resources[df_resources['Address'].str.contains('cdn')]
        if not cdn_usage.empty:
            return "Utilisation d'un CDN détectée"
        else:
            return "Aucun CDN détecté"
    except Exception as e:
        return f"Erreur lors de la vérification de l'utilisation d'un CDN : {e}"

def check_page_size(conn):
    try:
        df_pages = pd.read_sql_query("SELECT Address, TotalSize FROM Internal", conn)
        large_pages = df_pages[df_pages['TotalSize'] > 4 * 1024 * 1024]  # Pages de plus de 4 Mo
        if not large_pages.empty:
            return f"{len(large_pages)} pages dépassant 4 Mo"
        else:
            return "Toutes les pages sont inférieures à 4 Mo"
    except Exception as e:
        return f"Erreur lors de la vérification de la taille des pages : {e}"

def check_unused_scripts(conn):
    try:
        df_scripts = pd.read_sql_query("SELECT Address, UnusedScripts FROM Internal WHERE UnusedScripts IS NOT NULL", conn)
        if not df_scripts.empty:
            return f"{len(df_scripts)} pages avec des scripts inutilisés"
        else:
            return "Aucun script inutilisé détecté"
    except Exception as e:
        return f"Erreur lors de la vérification des scripts inutilisés : {e}"

def check_browser_cache(conn):
    try:
        df_headers = pd.read_sql_query("SELECT Address, CacheControl FROM Internal", conn)
        no_cache_pages = df_headers[df_headers['CacheControl'].isnull() | (df_headers['CacheControl'] == '')]

        if not no_cache_pages.empty:
            return f"{len(no_cache_pages)} pages sans cache navigateur activé"
        else:
            return "Toutes les pages ont le cache navigateur activé"
    except Exception as e:
        return f"Erreur lors de la vérification du cache navigateur : {e}"

def check_inline_css(conn):
    try:
        df_css = pd.read_sql_query("SELECT Address, InlineCSS FROM Internal", conn)
        pages_with_inline_css = df_css[df_css['InlineCSS'] > 0]
        if not pages_with_inline_css.empty:
            return f"{len(pages_with_inline_css)} pages avec du CSS en ligne"
        else:
            return "Aucune page avec du CSS en ligne"
    except Exception as e:
        return f"Erreur lors de la vérification du CSS en ligne : {e}"

def check_pagespeed_score(conn):
    try:
        df_speed = pd.read_sql_query("SELECT Address, PageSpeedScore FROM Internal", conn)
        low_score_pages = df_speed[df_speed['PageSpeedScore'] < 80]
        if not low_score_pages.empty:
            return f"{len(low_score_pages)} pages avec un score PageSpeed inférieur à 80"
        else:
            return "Toutes les pages ont un score PageSpeed supérieur à 80"
    except Exception as e:
        return f"Erreur lors de la vérification du score PageSpeed : {e}"

def check_dns_prefetching(conn):
    try:
        df_headers = pd.read_sql_query("SELECT Address, DNSPrefetch FROM Internal WHERE DNSPrefetch IS NOT NULL", conn)
        if not df_headers.empty:
            return "DNS Prefetching activé"
        else:
            return "DNS Prefetching non activé"
    except Exception as e:
        return f"Erreur lors de la vérification du DNS Prefetching : {e}"

def check_server_type(conn):
    try:
        df_headers = pd.read_sql_query("SELECT Address, Server FROM Internal", conn)
        if df_headers['Server'].str.contains('dedicated').any():
            return "Serveur dédié détecté"
        else:
            return "Serveur mutualisé détecté"
    except Exception as e:
        return f"Erreur lors de la vérification du type de serveur : {e}"
