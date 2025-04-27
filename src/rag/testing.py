import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
import re
import random
from googlesearch import search

from utils.helpers import get_git_root


class KYMScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def clean_template_name(self, template_url):
        """Extract and clean template name from URL"""
        name = template_url.split('/')[-1][:-4]  # Remove file extension
        # Convert to searchable format
        name = re.sub(r'[-_]', ' ', name)
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)  # Split camelCase
        return name.strip()

    def google_search_kym(self, template_name):
        """Search Google for KYM page"""
        try:
            query = f"{template_name} know your meme"

            # Search Google and get first KYM result
            search_results = search(query, num_results=5)

            # Find first KYM URL
            for url in search_results:
                print(f'Search result: {url}')
                if 'knowyourmeme.com/memes/' in url:
                    return url

            return None

        except Exception as e:
            print(f"Search error for {template_name}: {str(e)}")
            return None

    def get_about_section(self, url):
        """Extract about section from KYM page"""
        try:
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for the about section
            about_header = soup.find('h2', id='about')
            print(f"About header: {about_header}")
            if about_header:
                about_div = about_header.find_next('p')
                print(f"About div: {about_div}")
                if about_div:
                    # Clean the text
                    text = about_div.get_text(strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    print(text)
                    return text

            return None

        except Exception as e:
            print(f"Extraction error for {url}: {str(e)}")
            return None


def process_dataframe(df):
    """Process the DataFrame and update about sections"""
    scraper = KYMScraper()
    updates = 0
    errors = 0

    # Create a progress bar
    for index, row in tqdm(df.iterrows(), total=len(df)):
        if pd.isna(row['about']):
            try:
                # Extract and clean template name
                template_name = scraper.clean_template_name(row['template_url'])
                print(f'\nProcessing: {template_name}')
                # Search Google for KYM page
                kym_url = scraper.google_search_kym(template_name)
                print(f'Chosen URL: {kym_url}')

                asd = input("Other url:")
                if asd == "q":
                    continue

                if asd != "":
                    kym_url = asd

                if kym_url:
                    # Add random delay between requests (2-4 seconds)
                    time.sleep(random.uniform(2, 4))

                    # Get about section
                    about_text = scraper.get_about_section(kym_url)
                    print(f'About text: {about_text}')

                    if about_text:
                        df.at[index, 'about'] = about_text
                        updates += 1
                        print(f"\nUpdated: {template_name}")
                        print(f"URL: {kym_url}")

            except Exception as e:
                print(f"\nError processing row {index}: {str(e)}")
                errors += 1

            # Save progress periodically (every 5 updates)
            if updates % 5 == 0 and updates > 0:
                df.to_csv(root_path / 'data' / 'imkg' / 'processed' / 'imkg_final_proceessor.csv',
                          index=False)

    return df, updates, errors


if __name__ == "__main__":
    root_path = get_git_root()
    df = pd.read_csv(root_path / 'data' / 'imkg' / 'processed' / 'imkg_final_final_processed_with_matches.csv',
                     delimiter=',')

    print("Starting Google-based KYM scraping process...")
    updated_df, total_updates, total_errors = process_dataframe(df)

    # Save final plots
    output_path = root_path / 'data' / 'imkg' / 'processed' / 'imkg_final_proceessor.csv'
    updated_df.to_csv(output_path, index=False)

    print(f"\nScraping completed:")
    print(f"Total updates: {total_updates}")
    print(f"Total errors: {total_errors}")
    print(f"Results saved to: {output_path}")