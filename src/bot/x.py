import traceback
import random
import schedule
import time
import requests
from typing import List
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from bot.logger import log_print, setup_logging
from bot.scheduler import UpdateScheduler
from data.img_flip_memes import MemesDataManager
from data.virality_dataset import (parse_virality_dataset_entry, create_meme_virality_dataset, delete_meme_virality_dataset)
from data.schemas import Meme
from data.scrape_politifact import politifact_specific_article_scraper
from run_meme_fact import run_meme_fact
from utils.helpers import load_config, is_date_more_recent
from utils.x_api import XApi


def _select_meme(memes: List[Meme]) -> Meme | None:
    while True:
        choice = input("Enter the number of the meme you want to use (or 'q' to quit): ")

        if choice.lower() == 'q':
            log_print('Exited meme selection. Fact-checking aborted.')
            return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(memes):
                return memes[index]
            else:
                if len(memes) == 1:
                    print("Only one meme was generated. Please write 1.")
                else:
                    print(f"Please provide a number between 1 and {len(memes)} inclusive.")
        except ValueError:
            print("Invalid input. Please provide a positive integer or 'q' to quit.")


class XBot:

    def __init__(self):
        self.api = XApi()
        self.bot_config = load_config('x_bot.yaml')
        self.memes_manager = MemesDataManager()
        self.valid_verdicts = ['Pants on Fire!', 'False', 'Mostly False']
        self.post_text_templates = self.bot_config['post_text_template']
        self.starting_date = self.bot_config['starting_date']
        self.meme_fact_config = {'config': 'config.yaml', 'variant': self.bot_config['variant'],
                                 'moderate': self.bot_config['moderate'],
                                 'ablation': self.bot_config['ablation'],
                                 'bot': True,
                                 'num_memes': self.bot_config['num_memes']}
        self.bot_profile_base_url = 'https://x.com/pinto_serg4991/status/'
        self.update_scheduler = UpdateScheduler()

    def _get_random_template(self):
        tone = random.choice(['factual', 'humorous'])
        ai_mention = random.choice(['ai', 'no_ai'])
        return self.post_text_templates[tone][ai_mention]

    def _check_new_articles(self):

        base_url = 'https://www.politifact.com/factchecks/list/?page=1&speaker=tweets'
        politifact_base_url = 'https://www.politifact.com'
        articles_publish_dates = []
        articles_links = []
        new_articles = []

        response = requests.get(base_url)
        if response.status_code != 200:
            log_print(f'An error occured while scraping the web page {base_url}')
            return None
        webpage = BeautifulSoup(response.text, "html.parser")

        article_publish_date_footers = webpage.find_all('footer', attrs={'class': 'm-statement__footer'})
        claims_divs = webpage.find_all('div', attrs={'class': 'm-statement__quote'})

        for footer in article_publish_date_footers:
            link1 = footer.text.strip()
            parts = link1.split('•')

            if len(parts) != 2:
                log_print(f"Unexpected footer format: {link1}")
                continue

            date = parts[1]

            if is_date_more_recent(date, self.starting_date):
                articles_publish_dates.append(date)

        if not articles_publish_dates:
            log_print("There are not any recently published X Posts PolitiFact articles.")
            return None
        else:
            self.starting_date = articles_publish_dates[0]

        stop_index = len(articles_publish_dates)

        for i in range(stop_index):
            claim_div = claims_divs[i]
            a_tags = claim_div.find_all('a')

            if len(a_tags) != 1:
                log_print(f"Unexpected number of links in claim div: {a_tags}")
                continue

            url = a_tags[0].attrs['href']
            articles_links.append(politifact_base_url + url)

        if len(articles_links) != len(articles_publish_dates):
            log_print(
                f"Mismatch in number of articles ({len(articles_links)}) "
                f"and publish dates ({len(articles_publish_dates)}).")

        for i in range(len(articles_publish_dates)):
            new_articles.append({'publish_date': articles_publish_dates[i], 'article_link': articles_links[i]})

        return new_articles

    def _scrape_new_articles(self, new_articles):
        new_articles_parts = []
        cached_x_post_datas = []
        for article in new_articles:
            article_parts, cached_x_post_data = politifact_specific_article_scraper(article['article_link'], False)
            if not article_parts or not cached_x_post_data:
                continue
            else:
                article_parts = {**article_parts, **article}
            if article_parts.get('source') != 'X posts':
                log_print(
                    f"Article {article['article_link']} is not from X posts. "
                    f"Source: {article_parts.get('source')}")
                continue
            elif not article_parts['x_sources']:
                log_print(f'Article {article["article_link"]} has no X original sources {article_parts["x_sources"]}. '
                          f'They could have been deleted by the authors.')
                continue
            elif article_parts['verdict'] not in self.valid_verdicts:
                log_print(f'The given verdict {article_parts['verdict']} is not within the targeted verdicts.')
                continue
            new_articles_parts.append(article_parts)
            cached_x_post_datas.append(cached_x_post_data)
            log_print(
                f'For the article {article['article_link']} the original x sources are {article_parts['x_sources']}')
        return new_articles_parts, cached_x_post_datas

    def _fact_check_x_sources(self, url: str, verdict: str, x_sources_links: List, meme: Meme):
        results = []

        for post_link in x_sources_links:  # we are only scraping one source per article for now, thus
            # this loop will only have one iteration
            substituted_verdict = 'Completely False and Absurd' if verdict == 'Pants on Fire!' else verdict
            post_text = self._get_random_template().format(url=url, verdict=substituted_verdict)
            result = self.api.create_post(source_tweet_url=post_link, meme=meme,
                                          post_text=post_text)
            log_print(f'X API calls return data: {result}')
            if not result:
                log_print(f'Failed to create X posts for X post {post_link} of the article {url}.')
            else:
                log_print(f'Created successfully X posts for X post {post_link} of the article {url}.')
            results.append(result)
        return results

    def act(self):
        meme_image_urls = self.memes_manager.get_random_meme_image_url(self.bot_config['num_memes'])
        running_config = {'meme_images': meme_image_urls, **self.meme_fact_config}
        try:
            log_print("Starting to check for new articles...")
            new_articles = self._check_new_articles()
            if not new_articles:
                log_print("No new articles found.")
                return

            log_print(f"Found {len(new_articles)} new articles. Scraping details...")
            new_articles_parts, cached_x_datas = self._scrape_new_articles(new_articles)
            if not new_articles_parts:
                log_print("The new articles are not valid to fact-check.")
                return
            if not cached_x_datas:
                log_print("Failed to scrape data from the articles X sources.")
                return
            log_print(f"Processing {len(new_articles_parts)} articles for fact-checking...")

            for index, article_parts in enumerate(new_articles_parts):
                running_config = {'politifact': article_parts['article_link'], **running_config}
                memes = run_meme_fact(running_config)

                if len(memes) == 0:
                    log_print(f'MemeFact did not generate one meme.')
                    return

                meme = _select_meme(memes)
                if not meme:
                    return

                results = self._fact_check_x_sources(url=article_parts['article_link'],
                                                     verdict=article_parts['verdict'],
                                                     x_sources_links=article_parts['x_sources'],
                                                     meme=meme)
                if len(results) == 1 and len(results[0]) != 0:
                    parse_virality_dataset_entry(meme, cached_x_datas[index], results,
                                                 article_parts, self.bot_profile_base_url)
                    self.update_scheduler.schedule_updates(article_url=article_parts['article_link'],
                                                           meme_post_url=self.bot_profile_base_url + results[0][
                                                               'meme_post_response_data']['id'],
                                                           disclaimer_post_url=self.bot_profile_base_url + results[0][
                                                               'disclaimer_post_response_data']['id'])
            log_print("Finished action cycle.")
        except Exception as e:
            log_print(traceback.print_exc())
            log_print(e)

    def run(self):
        now = datetime.now()
        next_run = now + timedelta(minutes=1)
        schedule_time = next_run.strftime("%H:%M")

        log_print(f'XBot started. Scheduled to run daily at {schedule_time}.')
        schedule.every().day.at(schedule_time).do(self.act)
        try:
            while True:
                schedule.run_pending()
                time.sleep(60 * 60 * 3)
        except KeyboardInterrupt:
            log_print("Stopping XBot...")
            # delete_meme_virality_dataset('x_bot_data.csv')
            self.update_scheduler.stop_all_updates()


if __name__ == '__main__':
    create_meme_virality_dataset("x_bot_data.csv")
    setup_logging()
    bot = XBot()
    bot.run()
