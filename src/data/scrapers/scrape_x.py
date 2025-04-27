from typing import Dict
from playwright.sync_api import sync_playwright
from bot.logger import log_print


def parse_x_web_page(data) -> Dict:
    tweet_data = data['tweetResult']['result']
    user_data = tweet_data['core']['user_results']['result']
    legacy_tweet = tweet_data['legacy']
    legacy_user = user_data['legacy']
    tweet_info = {
        'tweet_id': tweet_data.get('rest_id', 0),
        'created_at': legacy_tweet.get('created_at', 0),
        'views_count': tweet_data.get('views', {}).get('count', 0),
        'favorite_count': legacy_tweet.get('favorite_count', 0),
        'retweet_count': legacy_tweet.get('retweet_count', 0),
        'quote_count': legacy_tweet.get('quote_count', 0),
        'reply_count': legacy_tweet.get('reply_count', 0),
        'bookmark_count': legacy_tweet.get('bookmark_count', 0),
    }

    if 'note_tweet' in tweet_data:
        tweet_info['full_text'] = tweet_data['note_tweet']['note_tweet_results']['result']['text']
    else:
        tweet_info['full_text'] = legacy_tweet['full_text']

    if 'birdwatch_pivot' in tweet_data:
        tweet_info['community_note'] = True
    else:
        tweet_info['community_note'] = False

    user_info = {
        'name': legacy_user['name'],
        'user_id': user_data['rest_id'],
        'created_at': legacy_user['created_at'],
        'followers_count': legacy_user['followers_count'],
        'description': legacy_user['description'],
        'is_blue_verified': user_data['is_blue_verified'],
    }

    return {
        'tweet': tweet_info,
        'user': user_info
    }


def scrape_x_page(url: str) -> Dict:
    try:
        xhr_calls = []

        def _intercept_back_calls(response):
            if response.request.resource_type == "xhr":
                xhr_calls.append(response)
            return response

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()

            page.on("response", _intercept_back_calls)
            page.goto(url)
            page.wait_for_selector("[data-testid='tweet']")

            tweet_calls = [f for f in xhr_calls if "TweetResultByRestId" in f.url]
            for xhr in tweet_calls:
                data = xhr.json()
                return parse_x_web_page(data['data'])
    except Exception as e:
        log_print(f'An Error ocurred while scraping the X page {url}. Error {e}.')
        return {}


if __name__ == '__main__':
    url = 'https://x.com/Meme__Fact/status/1862542618141306891'
    print(scrape_x_page(url))
