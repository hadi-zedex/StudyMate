import os
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams, QueryRequest

class QdrantStorage:
    def __init__(self, url=None, collection="docs", dim=384):
        url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY")  # None locally, set in production
        self.client = QdrantClient(url=url, api_key=api_key, timeout=30)
        self.collection_name = collection
        self.dim = dim

        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, ids, vectors, payloads):
        points= [PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) for i in range(len(ids))]
        self.client.upsert(self.collection_name, points=points)

    def search(self, query_vector, top_k: int=5):
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True
        ).points

        contexts=[]
        sources=set()

        for r in results:
            payload = r.payload or {}
            text = payload.get("text", "")
            source = payload.get("source", "")

            if text:
                contexts.append(text)
                sources.add(source)

        return {"contexts": contexts, "sources": list(sources)}
            

        
        

        
        