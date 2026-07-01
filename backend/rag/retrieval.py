from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from ..config.config import settings
from typing import List, Dict, Any

class ICDRetriever:
    def __init__(self):
        self.qclient = QdrantClient(url=settings.QDRANT_URL)
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def retrieve(self, query: str, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Performs hybrid retrieval for ICD codes in both CM and PCS collections.
        """
        results = {
            "cm": self._retrieve_collection(query, settings.QDRANT_COLLECTION_ICD10_CM, limit),
            "pcs": self._retrieve_collection(query, settings.QDRANT_COLLECTION_ICD10_PCS, limit)
        }
        return results

    def _retrieve_collection(self, query: str, collection_name: str, limit: int) -> List[Dict[str, Any]]:
        # Verify collection exists
        try:
            collections = self.qclient.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                return []
        except Exception:
            return []

        # Vector Search
        query_vector = self.model.encode(query).tolist()
        
        # Search Qdrant using modern query_points API
        response = self.qclient.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit * 2 # Retrieve more for hybrid merging
        )
        search_results = response.points
        
        # Parse results
        candidates = []
        seen = set()
        
        # Clean punctuation from words for better intersection while preserving inner dots/hyphens (e.g. codes)
        query_words = {w.strip(".,;:!?()[]{}'\"").lower() for w in query.split()}
        query_words.discard("")
        
        for hit in search_results:
            code = hit.payload.get("code")
            desc = hit.payload.get("description")
            type_str = hit.payload.get("type")
            
            if code in seen:
                continue
                
            seen.add(code)
            
            # Hybrid score boosting: if description words are exactly in query
            score = hit.score
            desc_words = {w.strip(".,;:!?()[]{}'\"").lower() for w in desc.split()}
            desc_words.discard("")
            
            intersection = query_words.intersection(desc_words)
            if intersection:
                # Boost score based on keyword overlap
                score += 0.05 * len(intersection)
                
            # If query contains the exact code as a token
            clean_code = code.strip(".,;:!?()[]{}'\"").lower()
            if clean_code in query_words:
                score += 0.5
                
            candidates.append({
                "code": code,
                "description": desc,
                "type": type_str,
                "score": score
            })
            
        # Re-sort based on hybrid score and truncate to limit
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:limit]

# Singleton instance
icd_retriever = ICDRetriever()
