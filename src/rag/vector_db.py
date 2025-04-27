import logging
import chromadb
import pandas as pd

from rag.knowledge_graph import get_git_root

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDB:
    def __init__(self, name='meme_fact_vector_db'):
        self.root_path = get_git_root()
        self.processed_data = self.root_path / 'data' / 'imkg' / 'processed' / 'imkg_final_final_final_processor.csv'
        self.vector_db_path = self.root_path / 'data' / 'vector_db'

        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.vector_db_path))

        self.collection = None

        try:
            self.collection = self.client.get_collection(name)
            logger.info(f"Loaded vector database: {name}")
        except Exception:
            logger.info(f"Vector database {name} not found. Creating new collection.")
            self._create_collection(name)

    def _create_collection(self, collection_name):
        self.collection = self.client.create_collection(name=collection_name)
        df = pd.read_csv(self.processed_data, delimiter=',')

        ids = []
        documents = []
        metadatas = []

        for _, row in df.iterrows():
            document_parts = [
                f"Meme Template Name: {row.template_title}",
                f"Meme Template/Image Visual Description: {row.description}",
                f"Meme Captioning Style: {row.caption_style_explanation}",
                f"Meme Number of Placeholders/Boxes/Captions to Fill: {row.box_count}",
            ]
            if not pd.isna(row.about):
                document_parts.insert(1, f"Meme KnowYourMeme about section: {row.about}")

            document = '\n\n'.join(document_parts)

            metadata = {
                'description': row.description,
                'captions': row.captions,
                'caption_style_explanation': row.caption_style_explanation,
                'box_count': row.box_count,
                'template_title': row.template_title,
                'url': row.template_url,
                'total_views': row.total_views,
                'total_upvotes': row.total_upvotes,
            }

            if not pd.isna(row.about):
                metadata['about'] = row.about

            ids.append(str(row.template_id))
            documents.append(document)
            metadatas.append(metadata)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def _query_by_template_id(self, meme_template_id):
        result = self.collection.get(
            ids=[meme_template_id],
            include=['metadatas']
        )
        if result and result['metadatas']:
            return [result['metadatas'][0]]
        return None

    def _query_by_article_data(self, article_data, nresults):
        query_parts = [f'Claim: {article_data["claim"]}']
        if 'iytis' in article_data:
            query_parts.append(f'Summarized rationale: {article_data["iytis"]}')
        if 'title' in article_data:
            query_parts.append(f'Article title: {article_data["title"]}')
        if 'verdict' in article_data:
            query_parts.append(f'Verdict: {article_data["verdict"]}')
        if 'iytis' not in article_data and 'rationale' in article_data:
            query_parts.append(f'Rationale: {article_data['rationale']}')
        if 'iytis' in article_data and 'rationale' in article_data:
            query_parts.append(f'Summarized rationale: {article_data["iytis"]}')
            query_parts.append(f'Rationale: {article_data['rationale']}')

        query_text = '\n'.join(query_parts)
        results = self.collection.query(
            query_texts=[query_text],
            n_results=nresults,
            include=['metadatas']
        )
        return [{**item, 'id': id} for item, id in zip(results['metadatas'][0], results['ids'][0])]

    def query(self, meme_template_id, article_data=None, nresults=1):
        if meme_template_id:
            ret = self._query_by_template_id(meme_template_id)
        else:
            ret = self._query_by_article_data(article_data, nresults)
        return ret if ret else None

    def add_entry(self, meme_template_id, description, captions, caption_style_explanation, box_count, template_title, url, total_views, total_upvotes, about=None):

        document_parts = [
            f"Meme Template Name: {template_title}",
            f"Meme Template/Image Visual Description: {description}",
            f"Meme Captioning Style: {caption_style_explanation}",
            f"Meme Number of Placeholders/Boxes/Captions to Fill: {box_count}",
        ]
        if about:
            document_parts.insert(1, f"Meme KnowYourMeme about section: {about}")

        document = '\n\n'.join(document_parts)

        metadata = {
            'description': description,
            'captions': captions,
            'caption_style_explanation': caption_style_explanation,
            'box_count': box_count,
            'template_title': template_title,
            'url': url,
            'total_views': total_views,
            'total_upvotes': total_upvotes,
        }

        if about:
            metadata['about'] = about

        self.collection.add(
            ids=[meme_template_id],
            documents=[document],
            metadatas=[metadata]
        )


if __name__ == '__main__':
    vector_db = VectorDB()
    #print(vector_db.query(meme_template_id='101440'))
    # print(
    #     vector_db.query(meme_template_id=None, article_data={'claim': 'claim', 'iytis': 'iytis', 'verdict': 'verdict'},
    #                     nresults=3))


    result = vector_db.collection.get(include=["metadatas"])
    # Count the number of documents by checking the length of the metadatas list.
    num_docs = len(result.get("metadatas", []))
    print("Number of documents in the vector DB:", num_docs)

