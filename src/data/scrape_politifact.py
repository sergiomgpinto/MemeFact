from bs4 import BeautifulSoup
from data.make_dataset import data_to_csv
import requests
import re


def parse_full_text(full_text_html):
    unwanted_sections = full_text_html.find_all(['section', 'div'], class_=['o-pick', 'm-statement'])
    for section in unwanted_sections:
        section.decompose()

    body_tags = full_text_html.find_all('body')
    body_texts = []

    for body in body_tags:
        for a in body.find_all('a'):
            a.replace_with(a.get_text())

        text = body.get_text(separator=' ', strip=True)
        text = re.sub(r'\(Read more about our partnership with Meta.*?\)', '', text)
        text = re.sub(r'RELATED:.*', '', text)
        text = re.sub(r'\s+', ' ', text)
        body_texts.append(text)

    full_text = ' '.join(body_texts)

    return full_text


def politifact_single_page_scraper(webpage):
    dates = []
    claims = []
    sources = []
    verdicts = []

    statement_footer = webpage.find_all('footer', attrs={'class': 'm-statement__footer'})
    statement_quote = webpage.find_all('div', attrs={'class': 'm-statement__quote'})
    statement_meta = webpage.find_all('div', attrs={'class': 'm-statement__meta'})
    statement_meter = webpage.find_all('div', attrs={'class': 'm-statement__meter'})

    if not statement_footer or not statement_quote or not statement_meta or not statement_meter:
        print(f'Errors encountered while scraping webpage.')
        return [], [], [], []

    for footer in statement_footer:  # get article date
        link1 = footer.text.strip()
        name_and_date = link1.split()
        month = name_and_date[4]
        day = name_and_date[5]
        year = name_and_date[6]
        date = month + ' ' + day + ' ' + year
        dates.append(date)

    for quote in statement_quote:  # get claims
        link2 = quote.find_all('a')
        claims.append(link2[0].text.strip())

    for meta in statement_meta:  # get sources of the claim
        link3 = meta.find_all('a')
        source_text = link3[0].text.strip()
        sources.append(source_text)

    for meter in statement_meter:  # get verdicts
        fact = meter.find('div', attrs={'class': 'c-image'}).find('img').get('alt')
        verdicts.append(fact)

    if not (len(dates) == len(claims) == len(sources) == len(verdicts)):
        print(f'Encountered errors while scraping a page.')
        return [], [], [], []

    return dates, claims, sources, verdicts


def politifact_article_scraper(webpage):
    short_texts = []
    full_texts = []
    articles_urls = [article['href'] for article in webpage.find_all('a', href=True)
                     if article['href'].startswith(('/factchecks/2023', '/factchecks/2024'))]

    for url in articles_urls:
        response = requests.get(f'https://www.politifact.com{url}')

        if response.status_code != 200:
            print(f'An error occured while getting the link {url}')
            break

        webpage = BeautifulSoup(response.text, 'html.parser')
        full_text_html = webpage.find('article', class_='m-textblock')

        if not full_text_html:
            print(f'There is no article full text section in the webpage https://www.politifact.com{url}.')
            full_texts.append(None)
        else:
            full_text = parse_full_text(full_text_html)
            full_texts.append(full_text)

        iytis_html = webpage.find('div', class_='short-on-time')

        if not iytis_html:
            print(f'There is no if-your-time-is-short section in the webpage https://www.politifact.com{url}.')
            short_texts.append(None)
        else:
            iytis = " ".join(iytis_html.get_text(separator=' ', strip=True).split())
            short_texts.append(iytis)

    return short_texts, full_texts


def politifact_specific_article_scraper(url):

    politifact_article = {}
    response = requests.get(f'{url}')

    if response.status_code != 200:
        print(f'An error occured while getting the link {url}')

    pattern = r"'Truth-O-Meter'\s*:\s*'([^']*)',"
    match = re.search(pattern, response.text)
    webpage = BeautifulSoup(response.text, 'html.parser')

    statement_date = webpage.find('span', attrs={'class': 'm-author__date'})
    statement_quote = webpage.find('div', attrs={'class': 'm-statement__quote'})
    statement_source = webpage.find('a', attrs={'class': 'm-statement__name'})
    full_text_html = webpage.find('article', class_='m-textblock')
    iytis_html = webpage.find('div', class_='short-on-time')

    if not statement_date or not statement_quote or not full_text_html or not iytis_html or not match or not statement_source:
        print(f'Errors encountered while scraping specific article {url}. It may be that it does not the'
              f' if-your-time-is-short section.')
        return {}

    politifact_article['source'] = statement_source.get_text(strip=True)
    politifact_article['verdict'] = match.group(1)
    politifact_article['date'] = statement_date.get_text(strip=True)
    politifact_article['claim'] = statement_quote.get_text(strip=True)
    politifact_article['rationale'] = parse_full_text(full_text_html)
    politifact_article['iytis'] = " ".join(iytis_html.get_text(separator=' ', strip=True).split())

    return politifact_article


def us_elections2024_full_page_scraper(page_number):
    url = 'https://www.politifact.com/factchecks/list/?page={}&category=elections'.format(str(page_number))

    response = requests.get(url)
    if response.status_code != 200:
        print(f'An error occured while getting the link {url}')
        return

    webpage = BeautifulSoup(response.text, "html.parser")
    dates, claims, sources, verdicts = politifact_single_page_scraper(webpage)
    if not dates:
        return [], [], [], [], [], []

    iytis, full_texts = politifact_article_scraper(webpage)
    if not (len(dates) == len(claims) == len(sources) == len(verdicts) == len(iytis) == len(full_texts)):
        print(f'Encountered some errors on the webpage number {page_number}.')
        return
    return dates, sources, claims, verdicts, iytis, full_texts


def us_presi_elections2024_politifact_scraper():
    all_dates, all_sources, all_claims, all_verdicts, all_iytis, all_full_texts = [], [], [], [], [], []

    for i in range(1, 8):  # the older pages were refering to other elections
        dates, sources, claims, verdicts, iytis, full_texts = us_elections2024_full_page_scraper(i)
        all_dates.extend(dates)
        all_sources.extend(sources)
        all_claims.extend(claims)
        all_verdicts.extend(verdicts)
        all_iytis.extend(iytis)
        all_full_texts.extend(full_texts)

    data_to_csv("politifact_us_presi_elections2024",
                date=all_dates,
                source=all_sources,
                claim=all_claims,
                verdict=all_verdicts,
                iytis=all_iytis,
                rationale=all_full_texts)


# if __name__ == "__main__":
    # us_presi_elections2024_politifact_scraper()
    # result = politifact_specific_article_scraper("https://www.politifact.com/factchecks/2024/sep/17/eric-hovde/does-the-baldwin-hovde-debate-take-place-after-vot/")
    # print(result)
