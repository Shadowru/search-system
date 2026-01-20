from rapidfuzz import fuzz
from app.utils.text import preprocess_text
from app.config import logger

class SearchService:
    def __init__(self, repository):
        self.repo = repository

    def fuzzy_search(self, query, limit=5):
        df = self.repo.get_all_systems_df()
        
        query_raw = preprocess_text(query, expand_synonyms=False)
        query_synonyms = preprocess_text(query, expand_synonyms=True)
        
        logger.info(f"Searching: Raw='{query_raw}' | Synonyms='{query_synonyms}'")
        
        results = []
        for _, row in df.iterrows():
            clean_title = preprocess_text(row['product_name'], expand_synonyms=False)
            clean_desc = preprocess_text(row['description'], expand_synonyms=False)
            clean_wiki = preprocess_text(row['wiki_content'], expand_synonyms=False)
            
            clean_ai = ""
            if row['ai_keywords']:
                clean_ai = preprocess_text(row['ai_keywords'], expand_synonyms=True)

            score_raw = max(
                fuzz.token_set_ratio(query_raw, clean_title),
                fuzz.token_set_ratio(query_raw, clean_desc)
            )
            
            score_syn = 0
            if query_raw != query_synonyms:
                score_syn = max(
                    fuzz.token_set_ratio(query_synonyms, clean_title),
                    fuzz.token_set_ratio(query_synonyms, clean_desc)
                )
            
            base_score = max(score_raw, score_syn)
            
            wiki_score = 0
            if clean_wiki:
                wiki_score = fuzz.token_set_ratio(query_synonyms, clean_wiki)
            
            score_ai = 0
            if clean_ai:
                score_ai = fuzz.token_set_ratio(query_synonyms, clean_ai)
            
            final_score = (base_score * 0.5) + (score_ai * 0.3) + (wiki_score * 0.2)
            
            status = str(row['status']).lower()
            if 'эксплуатации' in status or 'prod' in status:
                final_score += 5 
            
            if final_score > 45:
                res = row.to_dict()
                res['search_score'] = final_score
                results.append(res)
        
        results.sort(key=lambda x: x['search_score'], reverse=True)
        return results[:limit]