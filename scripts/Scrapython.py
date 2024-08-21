import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import gc
import logging
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Initialize a session for reusing connections
session = requests.Session()

# Setup retry strategy
retry_strategy = Retry(
    total=3,
    status_forcelist=[403, 404, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_text_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = session.get(url, headers=headers, timeout=5, verify=False)
        response.raise_for_status()

        # Handle specific HTTP errors
        if response.status_code in [403, 404]:
            logging.error(f"Error {response.status_code} for {url}")
            return url, [{"structure": "Error", "content": f"HTTP Error {response.status_code}"}]

        # Use BeautifulSoup to extract main content
        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = soup.get_text(strip=True)
        scraped_data = [{'structure': 'content', 'content': main_content}]

        gc.collect()  # Free memory
        return url, scraped_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {url}: {str(e)}")
        return url, [{"structure": "Error", "content": f"Request failed: {str(e)}"}]

def scrape_all_urls(urls):
    scraped_results = []
    max_workers = min(20, len(urls) // 10 + 1)  # Dynamically adjust the number of threads

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(scrape_text_from_url, url): url for url in urls}
        for future in as_completed(future_to_url):
            try:
                url, data = future.result()
                scraped_results.append((url, data))
            except Exception as e:
                scraped_results.append((future_to_url[future], [{"structure": "Error", "content": str(e)}]))

            gc.collect()  # Periodically collect memory

    return scraped_results

def create_output_df(urls, scraped_data_list):
    output_data = []
    for url, scraped_data in scraped_data_list:
        for data in scraped_data:
            output_data.append({
                'URL': url,
                'Structure': data['structure'],
                'Contenu Scrapé': data['content']
            })
    return pd.DataFrame(output_data)

def create_excel_file(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Scraped Data')
        writer.save()
    return output.getvalue()

def main():
    st.title("Advanced HTML Content Scraper")

    option = st.selectbox(
        "How would you like to provide the URLs?",
        ("Text Area", "Excel File")
    )

    urls = []

    if option == "Text Area":
        url_input = st.text_area("Enter the URLs to scrape (one per line)")
        if url_input:
            urls = list(filter(None, url_input.splitlines()))  # Remove empty lines

    elif option == "Excel File":
        uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            column_name = st.selectbox("Select the column containing the URLs", df.columns)
            urls = df[column_name].dropna().tolist()

    if st.button("Scrape"):
        if urls:
            # Process URLs in batches to avoid memory overflow
            batch_size = 10000  # Batch size for processing in parts
            total_batches = len(urls) // batch_size + 1
            all_scraped_data = []

            for batch_num in range(total_batches):
                batch_urls = urls[batch_num * batch_size: (batch_num + 1) * batch_size]
                scraped_data_list = scrape_all_urls(batch_urls)
                all_scraped_data.extend(scraped_data_list)

                # Free memory between batches
                gc.collect()

            if option == "Excel File":
                df['Structure'] = df[column_name].apply(lambda url: [data['structure'] for data in dict(all_scraped_data).get(url, [])])
                df['Contenu Scrapé'] = df[column_name].apply(lambda url: "\n".join([data['content'] for data in dict(all_scraped_data).get(url, [])]))
            else:
                df = create_output_df(urls, all_scraped_data)
            
            excel_data = create_excel_file(df)
            
            st.success("Scraping completed successfully! Download the file below.")
            st.download_button(
                label="Download Excel File",
                data=excel_data,
                file_name="scraped_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No URLs provided.")

if __name__ == "__main__":
    main()
