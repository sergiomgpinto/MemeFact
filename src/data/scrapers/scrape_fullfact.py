import requests
from bs4 import BeautifulSoup
from bot.logger import log_print
from data.scrapers.scrape_factcheck import clean_text


def scrape_fullfact_article(url):
    article_parts = {}
    response = requests.get(f'{url}')

    if response.status_code != 200:
        log_print(f'An error occured while getting the link {url}')

    webpage = BeautifulSoup(response.text, 'html.parser')

    title_element = webpage.find('title')
    if title_element:
        title = clean_text(title_element.text)
        title = title.replace(' – Full Fact', '')
        article_parts['title'] = title

    claim_title = webpage.find('h5', {'class': 'card-title'}, string='What was claimed')
    if claim_title:
        claim_text = claim_title.find_next('p', {'class': 'card-text'})
        if claim_text:
            article_parts['claim'] = clean_text(claim_text.text)

    verdict_title = webpage.find('h5', {'class': 'card-title'}, string='Our verdict')
    if verdict_title:
        verdict_text = verdict_title.find_next('p', {'class': 'card-text'})
        if verdict_text:
            article_parts['iytis'] = clean_text(verdict_text.text)

    date_element = webpage.find('div', {'class': 'timestamp mb-2'})

    if date_element:
        article_parts['date'] = clean_text(date_element.text)

    content_element = webpage.find('div', {'class': 'cms-content'})
    if content_element:
        rationale_paragraphs = []
        for p in content_element.find_all('p'):
            if p.find_parent('div', {'class': 'inline-donate'}):
                break
            rationale_paragraphs.append(clean_text(p.text))
        article_parts['rationale'] = ' '.join(rationale_paragraphs)
    if (not article_parts.get('title')
            or not article_parts.get('claim')
            or not article_parts.get('iytis')
            or not article_parts.get('date')
            or not article_parts.get('rationale')):
        return {}
    article_parts['url'] = url
    article_parts['fact_checker'] = 'FullFact'
    article_parts['verdict'] = ''

    return article_parts


if __name__ == '__main__':
    print(scrape_fullfact_article('https://fullfact.org/news/idf-soldiers-prisoners-image-ai-created/'))
