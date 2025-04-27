import csv
import math
import os
import traceback

import pytz
from typing import Optional
from dateutil import parser
from datetime import datetime
from data.scrapers.scrape_x import scrape_x_page
from data.schemas import Meme
from utils.helpers import get_git_root
from bot.logger import get_logger, log_print


logger = get_logger(__name__)


def _calculate_engagement_rate(num_views, num_likes, num_reposts, num_quote_tweets, num_replies):
    return num_views + num_likes + num_reposts + num_replies + num_quote_tweets


def _parse_update_fields(meme_post_url, disclaimer_post_url):
    try:
        meme_post_data = scrape_x_page(meme_post_url)
        disclaimer_post_data = scrape_x_page(disclaimer_post_url)

        if not meme_post_data or not disclaimer_post_data:
            raise Exception("Failed to scrape meme to update engagement metrics.")

        meme_post_data = meme_post_data['tweet']
        disclaimer_post_data = disclaimer_post_data['tweet']
        views_count = int(meme_post_data['views_count']) + int(disclaimer_post_data['views_count'])
        likes_count = int(meme_post_data['favorite_count']) + int(disclaimer_post_data['favorite_count'])
        retweets_count = int(meme_post_data['retweet_count']) + int(disclaimer_post_data['retweet_count'])
        quotes_count = int(meme_post_data['quote_count']) + int(disclaimer_post_data['quote_count'])
        replies_count = int(meme_post_data['reply_count']) + int(disclaimer_post_data['reply_count']) - 1  # -1 because
        # we are replying to our own post
        metrics = [views_count, likes_count, retweets_count, replies_count, quotes_count]
        engagement = _calculate_engagement_rate(num_views=views_count, num_likes=likes_count,
                                                num_reposts=retweets_count, num_quote_tweets=quotes_count,
                                                num_replies=replies_count)
        return metrics, engagement, False
    except Exception as e:
        logger.error(f"Error parsing tweet metrics: {str(e)}")
        return [0, 0, 0, 0, 0], 0, True


def update_1h_fields(article_url, meme_post_url, disclaimer_post_url):
    log_print(f'Running update_1h_fields for the article {article_url}.')
    metrics, engagement, error = _parse_update_fields(meme_post_url, disclaimer_post_url)
    update_meme_data('x_bot_data_10_03_15_46.csv', article_url, '1h', metrics, engagement, error)


def update_24h_fields(article_url, meme_post_url, disclaimer_post_url):
    log_print(f'Running update_24h_fields for the article {article_url}.')
    metrics, engagement, error = _parse_update_fields(meme_post_url, disclaimer_post_url)
    update_meme_data('x_bot_data_10_03_15_46.csv', article_url, '24h', metrics, engagement, error)


def update_7d_fields(article_url, meme_post_url, disclaimer_post_url):
    log_print(f'Running update_7d_fields for the article {article_url}.')
    metrics, engagement, error = _parse_update_fields(meme_post_url, disclaimer_post_url)
    update_meme_data('x_bot_data_10_03_15_46.csv', article_url, '7d', metrics, engagement, error)


def update_1m_fields(article_url, meme_post_url, disclaimer_post_url):
    log_print(f'Running update_1m_fields for the article {article_url}.')
    metrics, engagement, error = _parse_update_fields(meme_post_url, disclaimer_post_url)
    update_meme_data('x_bot_data_10_03_15_46.csv', article_url, '1m', metrics, engagement, error)


def update_3m_fields(article_url, meme_post_url, disclaimer_post_url):
    log_print(f'Running update_3m_fields for the article {article_url}.')
    metrics, engagement, error = _parse_update_fields(meme_post_url, disclaimer_post_url)
    update_meme_data('x_bot_data_10_03_15_46.csv', article_url, '3m', metrics, engagement, error)


def parse_virality_dataset_entry(meme: Meme, results, article_parts, bot_profile_base_url,
                                 x_post_template_tags, article_x_post_data, x_post_url):
    try:
        meme_post_results = results[0]['meme_post_response_data']
        disclaimer_post_results = results[0]['disclaimer_post_response_data']

        fact_check_timestamp = datetime.now()
        meme_post_url = bot_profile_base_url + meme_post_results['id']
        disclaimer_post_url = bot_profile_base_url + disclaimer_post_results['id']
        tweet_data = article_x_post_data['tweet']
        user_data = article_x_post_data['user']

        fact_check_article_url = article_parts['url']
        misinformation_username = user_data['name']
        original_misinformation_post_date = tweet_data['created_at']
        time_difference_hours = calculate_time_difference(original_misinformation_post_date)

        meme_upload_url = meme.get_url()
        meme_image_url = meme.get_meme_image().get_url()
        disclaimer_text = disclaimer_post_results['text']

        verdict = article_parts['verdict']
        x_post_tone = x_post_template_tags['tone']
        x_post_ai_gen_disclosure = x_post_template_tags['ai']

        add_meme_entry('x_bot_data_10_03_15_46.csv',
                       [
                           fact_check_timestamp,  # timestamp
                           meme_post_url,  # meme post url
                           disclaimer_post_url,  # disclaimer url
                           x_post_url,  # original misinformation post url
                           tweet_data['community_note'],  # "is_original_tweet_community_noted"
                           fact_check_article_url,  # fact check article url
                           misinformation_username,  # misinformation post username
                           user_data['user_id'],  # user_id
                           user_data['followers_count'],  # "user_followers_count"
                           user_data['is_blue_verified'],  # "is_user_blue_verified"
                           original_misinformation_post_date,
                           time_difference_hours,  # requires the above first
                           meme_upload_url,
                           meme_image_url,
                           disclaimer_text,
                           None,  # Misinformation topic tags
                           None, None, None, None, None,
                           # "views_1h", "likes_1h", "reposts_1h", "replies_1h", "quote_tweets_1h",
                           None, None, None, None, None,
                           # "views_24h", "likes_24h", "reposts_24h", "replies_24h", "quote_tweets_24h"
                           None, None, None, None, None,
                           # "views_7d", "likes_7d", "reposts_7d", "replies_7d", "quote_tweets_7d"
                           None, None, None, None, None,
                           # "views_1m", "likes_1m", "reposts_1m", "replies_1m", "quote_tweets_1m"
                           None, None, None, None, None,
                           # "views_3m", "likes_3m", "reposts_3m", "replies_3m", "quote_tweets_3m"
                           None,  # "engagement_growth_rate_24h"
                           None,  # "engagement_growth_rate_7d"
                           None,  # "engagement_growth_rate_1m"
                           None,  # "engagement_growth_rate_3m"
                           None,  # "reposted_by_user"
                           None,  # "liked_by_user"
                           None,  # "replied_by_user"
                           None,  # "blocked_by_user"
                           None,  # "followed_by_user"
                           None,  # "misinformation_post_deleted_by_user"
                           None,  # "reply_texts_meme_post"
                           None,  # "reply_texts_disclaimer_post"
                           verdict,  # "fact_check_verdict"
                           None,  # "meme_explains_verdict"
                           None,  # "meme_humor_rating"
                           None,  # "meme_relevance_rating"
                           x_post_tone,  # "x_post_tone"
                           x_post_ai_gen_disclosure,  # "x_post_ai_gen_disclosure"
                           False  # "meme_relevance_rating"
                       ])
        return True
    except Exception as e:
        log_print(traceback.print_exc())
        log_print(e)
        return False


def calculate_time_difference(date_string):
    given_date = parser.parse(date_string)

    given_date = given_date.replace(tzinfo=pytz.UTC)
    current_time = datetime.now(pytz.UTC)

    time_difference = current_time - given_date
    hours_difference = time_difference.total_seconds() / 3600
    return math.floor(hours_difference)


def create_meme_virality_dataset(filename):
    columns = [
        "fact_check_timestamp",  # When the fact-check meme was posted
        "meme_post_url",  # URL of the meme fact-check post
        "disclaimer_url",  # URL of the text disclaimer fact-check post
        "original_misinformation_post_url",
        "is_original_tweet_community_noted",
        "fact_check_article_url",
        "misinformation_user_username",
        "user_id",
        "user_followers_count",
        "is_user_blue_verified",
        "original_misinformation_post_date",
        "time_difference_hours",  # Time between original post and fact-check
        "meme_upload_url",  # Where the meme was actually posted
        "meme_image_url",  # Imgflip URL
        "disclaimer_text",
        "misinformation_topic_tags",  # e.g., "politics", "health", "environment"
        "views_1h", "likes_1h", "reposts_1h", "replies_1h", "quote_tweets_1h",
        "views_24h", "likes_24h", "reposts_24h", "replies_24h", "quote_tweets_24h",
        "views_7d", "likes_7d", "reposts_7d", "replies_7d", "quote_tweets_7d",
        "views_1m", "likes_1m", "reposts_1m", "replies_1m", "quote_tweets_1m",
        "views_3m", "likes_3m", "reposts_3m", "replies_3m", "quote_tweets_3m",
        "engagement_growth_rate_24h",  # (total_engagement_24h - total_engagement_1h) / 23
        "engagement_growth_rate_7d",  # (total_engagement_7d - total_engagement_24h) / 144
        "engagement_growth_rate_1m",
        "engagement_growth_rate_3m",
        "reposted_by_user",  # MANUAL
        "liked_by_user",  # MANUAL
        "replied_by_user",  # MANUAL
        "blocked_by_user",  # Boolean: True if blocked, False otherwise  MANUAL
        "followed_by_user",  # MANUAL
        "misinformation_post_deleted_by_user",  # MANUAL
        "reply_texts_meme_post",  # JSON string containing reply texts MANUAL
        "reply_texts_disclaimer_post",  # MANUAL
        "fact_check_verdict",
        "meme_explains_verdict",  # MANUAL
        "meme_humor_rating",  # MANUAL
        "meme_relevance_rating",  # MANUAL
        "x_post_tone",
        "x_post_ai_gen_disclosure",
        "error"
    ]
    root_path = get_git_root()
    save_dir = root_path / 'data' / 'bot' / 'dataset'
    save_dir.mkdir(parents=True, exist_ok=True)
    save_dir = save_dir / filename
    with open(str(save_dir), 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(columns)


def delete_meme_virality_dataset(filename):
    root_path = get_git_root()
    file_path = root_path / 'data' / 'bot' / 'dataset' / filename
    try:
        if file_path.exists():
            os.remove(file_path)
            print(f"Successfully deleted the file: {file_path}")
        else:
            print(f"File not found: {file_path}")
    except Exception as e:
        print(e)


def add_meme_entry(filename, entry_data):
    root_path = get_git_root()
    file_path = root_path / 'data' / 'bot' / 'dataset' / filename
    with file_path.open('a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(entry_data)


def update_meme_data(filename, article_url, time_point, metrics, engagement: Optional[int] = 0, error: bool = False):
    root_path = get_git_root()
    file_path = root_path / 'data' / 'bot' / 'dataset' / filename
    with file_path.open('r') as file:
        rows = list(csv.reader(file))

    for row in rows[1:]:
        if row[5] == article_url:
            if time_point == "1h":
                row[16:21] = metrics
            elif time_point == "24h":
                row[21:26] = metrics
                engagement_1h = sum(int(x) for x in row[16:21] if x)

                if engagement_1h > 0:
                    growth_rate = ((engagement - engagement_1h) / engagement_1h) * 100
                else:
                    growth_rate = 0 if engagement == 0 else 100
                row[41] = f'{growth_rate:.2f}%'
            elif time_point == "7d":
                row[26:31] = metrics
                engagement_24h = sum(int(x) for x in row[21:26] if x)
                if engagement_24h > 0:
                    growth_rate = ((engagement - engagement_24h) / engagement_24h) * 100
                else:
                    growth_rate = 0 if engagement == 0 else 100
                row[42] = f'{growth_rate:.2f}%'
            elif time_point == "1m":
                row[31:36] = metrics
                engagement_7d = sum(int(x) for x in row[26:31] if x)
                if engagement_7d > 0:
                    growth_rate = ((engagement - engagement_7d) / engagement_7d) * 100
                else:
                    growth_rate = 0 if engagement == 0 else 100
                row[43] = f'{growth_rate:.2f}%'
            elif time_point == "3m":
                row[36:41] = metrics
                engagement_1m = sum(int(x) for x in row[31:36] if x)
                if engagement_1m > 0:
                    growth_rate = ((engagement - engagement_1m) / engagement_1m) * 100
                else:
                    growth_rate = 0 if engagement == 0 else 100
                row[44] = f'{growth_rate:.2f}%'
            else:
                raise ValueError(f"Invalid time point: {time_point}")
            if error:
                row[59] = str(error)
            break

    with file_path.open('w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)


if __name__ == '__main__':
    create_meme_virality_dataset("x_bot_data_10_03_15_46.csv")
