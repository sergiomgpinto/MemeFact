import csv
import logging
import os
import subprocess
import re
import time
import pandas as pd
import yaml
from random import random
from heapq import heappush, heappushpop
from openai import OpenAI
from rdflib import Graph, RDF
from collections import Counter
from pathlib import Path

from utils.helpers import download_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""
This code was inspired by FactFlip by evhart
Source: https://github.com/evhart/factflip
Author: https://github.com/evhart
"""


def get_git_root() -> Path:
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'],
                                           stderr=subprocess.STDOUT).decode().strip()
        return Path(git_root)
    except subprocess.CalledProcessError:
        print("Warning: Not in a git repository. Using current working directory.")
        return Path.cwd()


def load_config(config_file: str):
    git_root = get_git_root()
    path = git_root / 'config' / config_file
    with open(path, 'r') as file:
        return yaml.safe_load(file)


def _parse_content(lines):
    sections = {}
    current_number = None
    current_content = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith(('1:', '2:', '3:', '4:', '5:')):
            if current_number:
                sections[current_number] = ' '.join(current_content)
                current_content = []
            current_number = line[0]
            current_content.append(line[3:])
        elif current_number:
            current_content.append(line)

    if current_number and current_content:
        sections[current_number] = ' '.join(current_content)

    return sections


def _merge_sections(sections):
    merged = []
    for i in range(1, 6):
        if str(i) in sections:
            merged.append(sections[str(i)])
    return ' '.join(merged)


def _clean_caption(text):
    text = ''.join(char for char in text if ord(char) < 128)
    return text.strip()


def prompt_gpt4o(prompt_template, row, client, no_input_image, max_retries=15):
    retries = 0
    while retries < max_retries:
        try:
            if no_input_image:
                content = [{"type": "text", "text": prompt_template}]
            else:
                content = [{"type": "text", "text": prompt_template}, {
                    "type": "image_url",
                    "image_url": {"url": row['template_url']}
                }]
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                max_tokens=1000,
                temperature=1.0
            )
            content = response.choices[0].message.content.strip()

            rejection_phrases = [
                "I'm sorry, but I can't",
                "I'm sorry, I can't",
                "I don't have information about",
                "I'm not able to",
                "I cannot provide",
                "I'm not comfortable",
                "I don't have access to",
                "I'm not authorized to",
                "I'm unable to analyze",
                "I'm unable to provide",
            ]
            if content and any(phrase in content for phrase in rejection_phrases):
                logger.warning(f"Attempt {retries + 1}: Model unable to analyze image. Retrying...")
                retries += 1
                continue

            return content
        except Exception as e:
            error_message = str(e)
            if not 'Error while downloading' in error_message:
                retries += 1
                logger.error(f"Error generating description for {row['template_url']}: {e}.")
            else:
                logger.error(f"Error generating description for {row['template_url']}: {e}.")
                return {}
    logger.error(f"Failed after {max_retries} attempts for {row['template_url']}")
    return {}


def _calculate_engagement(views, upvotes, views_mean, upvotes_mean, views_std, upvotes_std):
    if views == 0:
        return 0

    views_zscore = (views - views_mean) / views_std
    upvotes_zscore = (upvotes - upvotes_mean) / upvotes_std

    return float(0.2 * views_zscore + 0.8 * upvotes_zscore)


def _process_captions(captions):
    examples = captions.split('|||')

    formatted_examples = []
    for i, example in enumerate(examples, 1):
        variations = example.strip().split(';')
        formatted_variations = [f"Text box {j}: {var.strip()}"
                                for j, var in enumerate(variations, 1)]
        formatted_example = f"Example {i}:\n" + "\n".join(formatted_variations)
        formatted_examples.append(formatted_example)

    return "\n\n".join(formatted_examples)


class Imkg:

    def __init__(self):
        self.root_path = get_git_root()
        self.pre_processed_imkg_path = self.root_path / 'data' / 'imkg' / 'rdf' / 'full'
        self.processed_imkg_path = self.root_path / 'data' / 'imkg' / 'processed' / 'imkg.ttl'
        self.BASE_MEME_TEMPLATE_URL = 'https://imgflip.com/s/meme/{}.jpg'
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.config = load_config('imkg.yaml')

        if not self.processed_imkg_path.exists():
            self.kg = self.parse()
        else:
            self.kg = self.load()

        if not (self.root_path / 'data' / 'imkg' / 'processed' / 'imkg.csv').exists():
            self.query_kg()
        self.data = pd.read_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg.csv')
        if (self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_descriptions.csv').exists():
            self.data_descriptions = pd.read_csv(
                self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_descriptions.csv')

    def parse(self) -> Graph:
        logger.info("Parsing IMKG.")
        g = Graph()
        for subdir, _, files in os.walk(self.pre_processed_imkg_path):
            for file in files:
                ext = os.path.splitext(file)[-1].lower()
                if ext in [".nt", ".ttl"]:
                    g.parse(os.path.join(subdir, file), format=ext[1::])
                    logger.info(f"Parsed: {file}.")
        g.serialize(self.processed_imkg_path, format="ttl")
        logger.info(f"Serialized graph to {self.processed_imkg_path}.")
        return g

    def load(self):
        g = Graph()
        logger.info("Loading IMKG.")
        g.parse(self.processed_imkg_path, format="ttl")
        logger.info("Completed loading IMKG.")
        return g

    def metrics(self):
        print("=== PREDICATES (Properties) ===")
        predicates = set(p for _, p, _ in self.kg)
        for p in predicates:
            print(f"Predicate: {p}")

        print("\n=== TYPES ===")
        types = set(o for _, p, o in self.kg if p == RDF.type)
        for t in types:
            print(f"Type: {t}")

        print("\n=== PREDICATE USAGE COUNT ===")
        pred_count = Counter(str(p) for _, p, _ in self.kg)
        for pred, count in pred_count.most_common():
            print(f"{pred}: {count} instances")

        print("\n=== SAMPLE TRIPLES ===")
        for p in predicates:
            for s, _, o in self.kg.triples((None, p, None)):
                print(f"Subject: {s}\nPredicate: {p}\nObject: {o}\n")
                break  # Just get one example per predicate

        print("\n=== STATISTICS ===")
        print(f"Total triples: {len(self.kg)}")
        print(f"Unique subjects: {len(set(s for s, _, _ in self.kg))}")
        print(f"Unique predicates: {len(predicates)}")
        print(f"Unique objects: {len(set(o for _, _, o in self.kg))}")

    def query_kg(self):
        logger.info("Querying IMKG.")
        query = """
                SELECT ?img_flip_meme ?kym_meme ?template_title ?image_url ?template_id ?view_count ?upvote_count ?alt_text ?about ?punctuation_cleaned 
                WHERE 
                {
                    ?img_flip_meme ns1:template_title ?template_title ;
                          ns1:image_url ?image_url ;
                          ns1:templateId ?template_id ;
                          ns1:view_count ?view_count ;
                          ns1:upvote_count ?upvote_count ;
                          ns1:alt_text ?alt_text .

                    BIND(LCASE(?template_title) as ?lower_title)
                    BIND(REPLACE(?lower_title, " ", "-") as ?space_cleaned)
                    BIND(REPLACE(?space_cleaned, '"', "") as ?quotes_cleaned)  
                    BIND(REPLACE(?quotes_cleaned, "[!?,]", "") as ?punctuation_cleaned) 
                    BIND(IRI(CONCAT(STR(kym:), ?punctuation_cleaned)) as ?kym_meme)

                    ?kym_meme a kym:Meme ; m4s:about ?about .
                }
                """

        data = []
        res = self.kg.query(query)
        for row in res:
            if (match := re.search(r"^ *([^|]+) *\| *([^|]+) *\| *image tagged in *([^|]+) *\|[^|]*$",
                                   row.alt_text.strip(),
                                   re.IGNORECASE)):
                captions_text = match.group(2).strip()
                template_title = row.template_title.toPython()
                data.append({
                    'meme_url': row.img_flip_meme.toPython().strip(),
                    'kym_url': row.kym_meme.toPython().strip(),
                    'meme_image_url': row.image_url.toPython().strip(),
                    'template_id': row.template_id.toPython().strip(),
                    'template_title': template_title.strip(),
                    'template_url': self.BASE_MEME_TEMPLATE_URL.format(row.punctuation_cleaned.toPython().strip()),
                    'captions': captions_text,
                    'about': row.about.toPython().strip(),
                    'views': (
                        0 if row.view_count.toPython() == "NA" else int(row.view_count.toPython().replace(",", ""))),
                    'upvotes': (
                        0 if row.upvote_count.toPython() == "NA" else int(
                            row.upvote_count.toPython().replace(",", ""))),
                })
        logger.info("Completed querying IMKG.")

        pd.DataFrame(data).to_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg.csv', index=False, header=True)

    def query_imkg_memes(self):
        logger.info("Querying IMKG memes.")
        query = """
                SELECT ?img_flip_meme ?template_title ?image_url ?view_count ?upvote_count ?alt_text
                WHERE 
                {
                    ?img_flip_meme ns1:template_title ?template_title ;
                          ns1:image_url ?image_url ;
                          ns1:view_count ?view_count ;
                          ns1:upvote_count ?upvote_count ;
                          ns1:alt_text ?alt_text .
                }
                """

        data = []
        res = self.kg.query(query)
        for row in res:
            if (match := re.search(r"^ *([^|]+) *\| *([^|]+) *\| *image tagged in *([^|]+) *\|[^|]*$",
                                   row.alt_text.strip(),
                                   re.IGNORECASE)):
                captions_text = match.group(2).strip()
                data.append({
                    'meme_url': row.img_flip_meme.toPython().strip(),
                    'meme_image_url': row.image_url.toPython().strip(),
                    'template_title': row.template_title.toPython().strip(),
                    'captions': captions_text,
                    'views': (
                        0 if row.view_count.toPython() == "NA" else int(row.view_count.toPython().replace(",", ""))),
                    'upvotes': (
                        0 if row.upvote_count.toPython() == "NA" else int(
                            row.upvote_count.toPython().replace(",", ""))),
                })
        logger.info("Completed querying IMKG memes.")

        pd.DataFrame(data).to_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_memes.csv', index=False,
                                  header=True)

    def query_imkg_templates(self):
        logger.info("Querying IMKG meme templates.")
        query = """
                SELECT DISTINCT ?template_title ?template_id ?punctuation_cleaned
                WHERE 
                {
                    ?img_flip_meme ns1:template_title ?template_title ;
                          ns1:templateId ?template_id .
                          
                    BIND(LCASE(?template_title) as ?lower_title)
                    BIND(REPLACE(?lower_title, " ", "-") as ?space_cleaned)
                    BIND(REPLACE(?space_cleaned, '"', "") as ?quotes_cleaned)  
                    BIND(REPLACE(?quotes_cleaned, "[!?,]", "") as ?punctuation_cleaned)    
                }
                """

        data = []
        res = self.kg.query(query)
        for row in res:
            data.append({
                'template_title': row.template_title.toPython().strip(),
                'template_id': row.template_id.toPython().strip(),
                'template_url': self.BASE_MEME_TEMPLATE_URL.format(row.punctuation_cleaned.toPython().strip()),
            })
        logger.info("Completed querying IMKG meme templates.")

        pd.DataFrame(data).to_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_meme_templates.csv',
                                  index=False, header=True)

    def query_kym_memes(self):
        logger.info("Querying IMKG kym memes.")
        query = """
                SELECT DISTINCT ?kym_meme ?about 
                WHERE 
                {
                    ?kym_meme a kym:Meme ; m4s:about ?about .  
                }
                """

        data = []
        res = self.kg.query(query)
        for row in res:
            data.append({
                'kym_url': row.kym_meme.toPython().strip(),
                'about': row.about.toPython().strip(),
            })
        logger.info("Completed querying IMKG kym memes.")

        pd.DataFrame(data).to_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_kym_memes.csv',
                                  index=False, header=True)

    def query_templates_top_captions(self, n):
        logger.info(f"Querying top {n} captions per template.")
        df = pd.read_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_memes.csv')
        views_mean = df['views'].mean()
        upvotes_mean = df['upvotes'].mean()
        views_std = df['views'].std()
        upvotes_std = df['upvotes'].std()
        data = {}

        for _, row in df.iterrows():
            template_title = row['template_title']
            engagement = _calculate_engagement(row['views'], row['upvotes'], views_mean, upvotes_mean, views_std,
                                               upvotes_std)
            meme_data = {
                'meme_url': row['meme_url'],
                'views': row['views'],
                'upvotes': row['upvotes'],
                'captions': row['captions'],
                'engagement': engagement,
            }
            if template_title not in data:
                data[template_title] = []

            if len(data[template_title]) < n:
                heappush(data[template_title], (meme_data['engagement'], random(), meme_data))
            else:
                heappushpop(data[template_title], (meme_data['engagement'], random(), meme_data))

        rows = []
        for template, heap in data.items():
            sorted_memes = sorted(heap, key=lambda x: x[0])
            for meme in sorted_memes:
                rows.append({
                    'template_title': template,
                    'meme_url': meme[2]['meme_url'],
                    'views': meme[2]['views'],
                    'upvotes': meme[2]['upvotes'],
                    'engagement': meme[2]['engagement'],
                    'captions': meme[2]['captions']
                })

        pd.DataFrame(rows).to_csv(
            self.root_path / 'data' / 'imkg' / 'processed' / f'imkg_top_{n}_captions_per_template.csv',
            index=False, header=True)
        logger.info(f"Completed querying top {n} captions per template.")

    def generate_image_descriptions(self):
        logger.info("Generating meme template descriptions.")
        df = pd.read_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_meme_templates.csv')
        rows = []
        prompt_template = self.config['prompt_meme_description']

        try:
            for _, row in df.iterrows():
                ret = prompt_gpt4o(prompt_template, row, self.client)
                if not ret:
                    logger.info(f"Unable to generate description for meme template {row['template_url']}.")
                    rows.append({
                        'template_url': row['template_url'],
                        'description': " UNABLE TO DESCRIBE MEME TEMPLATE"
                    })
                else:
                    rows.append({
                        'template_url': row['template_url'],
                        'description': ret['description']
                    })
                    logger.info(f"Generated description for meme template {row['template_url']}.")

            pd.DataFrame(rows).to_csv(
                self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_meme_templates_descriptions.csv',
                index=False, header=True)
            logger.info("Completed generating meme image descriptions.")
        except KeyboardInterrupt:
            logger.info("Process interrupted. Saving current progress...")
        finally:
            if rows:
                pd.DataFrame(rows).to_csv(
                    self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_meme_templates_descriptions.csv',
                    index=False, header=True)

    def generate_meme_style_explanation(self):
        logger.info("Generating meme style usage explanations.")
        # df_meme_templates = pd.read_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_meme_templates.csv')
        # df_captions = pd.read_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_top_10_captions_per_template.csv')
        # df_descriptions = pd.read_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_meme_templates_descriptions.csv')
        #
        # grouped_captions = df_captions.groupby('template_title').agg({
        #     'captions': lambda x: ' ||| '.join(_clean_caption(text) for text in x),
        #     'views': 'sum',
        #     'upvotes': 'sum'
        # }).reset_index()
        #
        # merged_df = pd.merge(
        #     df_meme_templates[['template_id', 'template_url', 'template_title']],
        #     grouped_captions[['template_title', 'captions', 'views', 'upvotes']],
        #     on='template_title',
        #     how='inner')
        #
        # final_df = pd.merge(merged_df,
        #                     df_descriptions[df_descriptions['description'] != " UNABLE TO DESCRIBE MEME TEMPLATE"][
        #                         ['template_url', 'description']],
        #                     on='template_url',
        #                     how='inner')
        #
        # final_df = final_df[
        #     ['template_id', 'template_url', 'template_title', 'views', 'upvotes', 'captions', 'description']]
        # final_df = final_df.rename(columns={'views': 'total_views', 'upvotes': 'total_upvotes'})
        #
        # pd.DataFrame.to_csv(final_df, self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_proccessed.csv', index=False, header=True,
        #                     quoting=csv.QUOTE_MINIMAL,
        #                     escapechar='\\')
        rows = []
        df = pd.read_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_proccessed.csv', delimiter=',')

        try:
            for index, row in df.iterrows():
                prompt_template = self.config['prompt_meme_explanation'].format(
                    meme_image_description=row['description'],
                    meme_captions=_process_captions(row['captions']))
                ret = prompt_gpt4o(prompt_template, row, self.client)
                if not ret:
                    logger.info(
                        f"Unable to generate explanation for the caption style of the meme template {row['template_url']}.")
                    rows.append({
                        **row,
                        'caption_style_explanation': " UNABLE TO GENERATE EXPLANATION"
                    })
                else:
                    rows.append({
                        **row,
                        'caption_style_explanation': ret['description']
                    })
                    logger.info(
                        f"Generated explanation for the caption style of the meme template {row['template_url']}.")

            df.to_csv(
                self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_final_proccessed.csv',
                index=False, header=True,
                quoting=csv.QUOTE_MINIMAL,
                escapechar='\\')
            logger.info("Completed generating meme captioning style usage explanations.")
        except KeyboardInterrupt:
            logger.info("Process interrupted. Saving current progress...")
            df.to_csv(
                self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_final_proccessed.csv',
                index=False,
                header=True,
                quoting=csv.QUOTE_MINIMAL,
                escapechar='\\'
            )
            logger.info("Saved current progress for interrupted process.")

    def add_kym_about_section(self):
        df = pd.read_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_final_deduplicated_proccessed.csv',
                         delimiter=',')
        imkg = pd.read_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg.csv', delimiter=',')
        nrows = len(df)
        for index, row in df.iterrows():
            start = time.time()
            template_title = row['template_title']
            for _, row_imkg in imkg.iterrows():
                if row_imkg['template_title'] == template_title:
                    about = row_imkg['about']
                    df.at[index, 'about'] = about
                    break
            finish = time.time()
            nrows -= 1
            print(f"Processed {template_title} in {finish - start} seconds. {nrows} rows left.")
            print(f'Estimated time left: {nrows * (finish - start) / 60} minutes.')

        columns = ['template_id', 'template_url', 'template_title', 'total_views', 'total_upvotes', 'about', 'captions',
                   'description', 'caption_style_explanation']
        df.to_csv(self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_final_final_proccessed.csv', index=False,
                  header=True, columns=columns)


if __name__ == "__main__":
    # root_path = get_git_root()
    #
    # df = pd.read_csv(root_path / 'data' / 'imkg' / 'processed' / 'imkg_final_final_final_processor.csv',
    #                  delimiter=',')
    # counter = 0
    # root_path = get_git_root()
    # meme_images_path = root_path / 'data' / 'raw' / 'meme_images'
    # meme_images_path.mkdir(parents=True, exist_ok=True)
    # for index, row in df.iterrows():
    #     download_image(row['template_url'], row['template_title'], meme_images_path)
    kg = Imkg()
    kg.metrics()