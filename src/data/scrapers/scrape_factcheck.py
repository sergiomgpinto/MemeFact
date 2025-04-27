import requests
from bs4 import BeautifulSoup
from bot.logger import log_print


def clean_text(text: str) -> str:
    if isinstance(text, str):
        return text.replace('\xa0', ' ').strip()
    return text


def scrape_factcheck_article(url):
    article_parts = {}
    response = requests.get(f'{url}')

    if response.status_code != 200:
        log_print(f'An error occured while getting the link {url}')

    webpage = BeautifulSoup(response.text, 'html.parser')

    title_element = webpage.find('h1', class_='entry-title')
    if title_element:
        article_parts['title'] = clean_text(title_element.text)

    quick_take_heading = webpage.find('h2', class_='wp-block-heading', string='Quick Take')
    if quick_take_heading:
        quick_take_text = quick_take_heading.find_next('p')
        if quick_take_text:
            article_parts['iytis'] = clean_text(quick_take_text.text)

    full_story_heading = webpage.find('h2', class_='wp-block-heading', string='Full Story')
    if full_story_heading:
        full_story_content = []
        current_element = full_story_heading.find_next('p')

        while current_element and (not current_element.name == 'h2'):
            if current_element.name == 'p':
                full_story_content.append(clean_text(current_element.text))
            current_element = current_element.find_next()

        article_parts['rationale'] = ' '.join(full_story_content)

    date_element = webpage.find('time', class_='entry-date')
    if date_element:
        formatted_date = clean_text(date_element.text)
        article_parts['date'] = formatted_date

    article_parts['url'] = url
    article_parts['fact_checker'] = 'FactCheck'
    article_parts['verdict'] = ''
    article_parts['claim'] = ''

    return article_parts


if __name__ == '__main__':
    scrape_factcheck_article('https://www.factcheck.org/2024/10/posts-misrepresent-federal-response-funding-for-hurricane-helene-victims/')
