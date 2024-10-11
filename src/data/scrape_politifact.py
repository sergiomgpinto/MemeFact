import requests
import re
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from bot.logger import get_logger, log_print
from bot.scrape_x import scrape_x_page
from data.csv import data_to_csv


logger = get_logger(__name__)


def _is_claim_in_text(claim, full_text, threshold=0.8):
    claim = claim.lower()
    full_text = full_text.lower()

    if claim in full_text:
        return True

    matcher = SequenceMatcher(None, claim, full_text)
    for i, j, n in matcher.get_matching_blocks():
        match = full_text[j:j + n]
        if len(match) / len(claim) > threshold:
            return True
    return False


def _parse_x_posts_links(section, claim):
    p_tags = section.find_all('p')
    links = []
    cached_x_post_data = None
    for p in p_tags:
        a_tags = p.find_all('a')
        if ((len(a_tags) == 2 and a_tags[0].text == 'X post' and 'archived' in a_tags[1].text) or
                (len(a_tags) == 1 and a_tags[0].text == 'post')):
            x_post_link = a_tags[0]['href']
            if x_post_link not in links and len(links) == 0:
                data = scrape_x_page(x_post_link)
                cached_x_post_data = data
                tweet_text = data['tweet']['full_text']
                if _is_claim_in_text(claim, tweet_text):
                    links.append(x_post_link)
    if not links:
        log_print(f'The original X post sources with the article claim no longer exist.')
    return links, cached_x_post_data


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
        log_print(f'Errors encountered while scraping webpage.')
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
        log_print(f'Encountered errors while scraping a page.')
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
            log_print(f'An error occured while getting the link {url}')
            break

        webpage = BeautifulSoup(response.text, 'html.parser')
        full_text_html = webpage.find('article', class_='m-textblock')

        if not full_text_html:
            log_print(f'There is no article full text section in the webpage https://www.politifact.com{url}.')
            full_texts.append(None)
        else:
            full_text = parse_full_text(full_text_html)
            full_texts.append(full_text)

        iytis_html = webpage.find('div', class_='short-on-time')

        if not iytis_html:
            log_print(f'There is no if-your-time-is-short section in the webpage https://www.politifact.com{url}.')
            short_texts.append(None)
        else:
            iytis = " ".join(iytis_html.get_text(separator=' ', strip=True).split())
            short_texts.append(iytis)

    return short_texts, full_texts


def politifact_specific_article_scraper(url, disable_x_sources_scraping):

    politifact_article = {}
    response = requests.get(f'{url}')

    if response.status_code != 200:
        log_print(f'An error occured while getting the link {url}')

    pattern = r"'Truth-O-Meter'\s*:\s*'([^']*)',"
    match = re.search(pattern, response.text)
    webpage = BeautifulSoup(response.text, 'html.parser')
    statement_date = webpage.find('span', attrs={'class': 'm-author__date'})
    statement_quote = webpage.find('div', attrs={'class': 'm-statement__quote'})
    statement_source = webpage.find('a', attrs={'class': 'm-statement__name'})
    original_sources_section = webpage.find('section', attrs={'class': 'm-superbox', 'id': 'sources'})
    c_tags = webpage.find_all('a', attrs={'class': 'c-tag'})
    full_text_html = webpage.find('article', class_='m-textblock')
    iytis_html = webpage.find('div', class_='short-on-time')

    if (not statement_date or not statement_quote or not full_text_html or not iytis_html
            or not match or not statement_source or not original_sources_section or not c_tags):
        log_print(f'Errors encountered while scraping specific article {url}.')
        return {}, []

    for c_tag in c_tags:
        title = c_tag['title']
        if title == 'PolitiFact en Español':
            log_print(f'The article {url} is in spanish. Will not be considered.')
            return {}, []
    politifact_article['source'] = statement_source.get_text(strip=True)
    politifact_article['verdict'] = match.group(1)
    politifact_article['date'] = statement_date.get_text(strip=True)
    politifact_article['claim'] = statement_quote.get_text(strip=True)
    politifact_article['rationale'] = parse_full_text(full_text_html)
    politifact_article['iytis'] = " ".join(iytis_html.get_text(separator=' ', strip=True).split())

    if disable_x_sources_scraping:
        return politifact_article, {}
    else:
        x_sources, cached_x_post_data = _parse_x_posts_links(original_sources_section, politifact_article['claim'])
        politifact_article['x_sources'] = x_sources
        return politifact_article, cached_x_post_data


def us_elections2024_full_page_scraper(page_number):
    url = 'https://www.politifact.com/factchecks/list/?page={}&category=elections'.format(str(page_number))

    response = requests.get(url)
    if response.status_code != 200:
        log_print(f'An error occured while getting the link {url}')
        return [], [], [], [], [], []

    webpage = BeautifulSoup(response.text, "html.parser")
    dates, claims, sources, verdicts = politifact_single_page_scraper(webpage)
    if not dates:
        return [], [], [], [], [], []

    iytis, full_texts = politifact_article_scraper(webpage)
    if not (len(dates) == len(claims) == len(sources) == len(verdicts) == len(iytis) == len(full_texts)):
        log_print(f'Encountered some errors on the webpage number {page_number}.')
        return [], [], [], [], [], []
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
