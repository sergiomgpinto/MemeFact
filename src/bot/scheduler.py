import threading
import traceback
from datetime import datetime
from bot.logger import get_logger, log_print
from data.virality_dataset import (update_1h_fields, update_24h_fields,
                                   update_7d_fields, update_1m_fields, update_3m_fields)


logger = get_logger(__name__)


class UpdateScheduler:
    def __init__(self):
        self.scheduled_updates = {}

    def _schedule_update(self, delay, update_function, *args):
        timer = threading.Timer(delay, self._run_update, args=[update_function] + list(args))
        timer.start()
        self.scheduled_updates[args[0]].append(timer)

    def _run_update(self, update_function, *args):
        article_url = args[0]

        try:
            update_function(*args)
            log_print(f"Completed {update_function.__name__} update for post {article_url} at {datetime.now()}.")
        except Exception as e:
            print(traceback.print_exc())
            log_print(f"Error in scheduled update for article {article_url}: {e}")
        finally:
            if article_url in self.scheduled_updates:
                self.scheduled_updates[article_url] = [t for t in self.scheduled_updates[article_url] if t.is_alive()]
                if not self.scheduled_updates[article_url]:
                    del self.scheduled_updates[article_url]

    def schedule_updates(self, article_url, meme_post_url, disclaimer_post_url):
        self.scheduled_updates[article_url] = []
        self._schedule_update(1 * 60 * 60, update_1h_fields, article_url,
                              meme_post_url, disclaimer_post_url)
        self._schedule_update(24 * 60 * 60, update_24h_fields, article_url,
                              meme_post_url, disclaimer_post_url)
        self._schedule_update(7 * 24 * 60 * 60, update_7d_fields, article_url,
                              meme_post_url, disclaimer_post_url)
        self._schedule_update(30 * 24 * 60 * 60, update_1m_fields, article_url,
                              meme_post_url, disclaimer_post_url)
        self._schedule_update(90 * 24 * 60 * 60, update_3m_fields, article_url,
                              meme_post_url, disclaimer_post_url)

    def stop_all_updates(self):
        for article_url, timers in self.scheduled_updates.items():
            for timer in timers:
                timer.cancel()
        self.scheduled_updates.clear()
