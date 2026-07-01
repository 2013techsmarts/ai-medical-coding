import os
import argparse
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from ..config.config import settings
from .parser import load_all_codes
from langfuse import Langfuse
import uuid

# Initialize Langfuse client
langfuse = None
if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
    langfuse = Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST
    )

def ingest_codes(type_str: str):
    print(f"Starting ingestion for: {type_str}")
    
    # 1. Parse files
    if type_str == "cm":
        dir_path = settings.ICD10_CM_PATH
        collection_name = settings.QDRANT_COLLECTION_ICD10_CM
    elif type_str == "pcs":
        dir_path = settings.ICD10_PCS_PATH
        collection_name = settings.QDRANT_COLLECTION_ICD10_PCS
    else:
        raise ValueError(f"Invalid type: {type_str}")
        
    print(f"Scanning directory: {dir_path}")
    raw_codes = load_all_codes(dir_path, type_str)
    print(f"Found {len(raw_codes)} codes to ingest.")
    
    if not raw_codes:
        print("No codes found. Exiting.")
        return

    # Create trace in Langfuse
    span = None
    if langfuse:
        try:
            span = langfuse.start_observation(
                as_type="span",
                name="icd_ingestion",
                metadata={"type": type_str, "file_count": len(raw_codes)}
            )
        except Exception as e:
            print(f"Failed to start Langfuse trace: {e}")

    # 2. Init Qdrant Client
    print(f"Connecting to Qdrant at: {settings.QDRANT_URL}")
    qclient = QdrantClient(url=settings.QDRANT_URL)
    
    # Check collection
    vector_size = 384
    
    collections = qclient.get_collections().collections
    exists = any(c.name == collection_name for c in collections)
    if not exists:
        print(f"Creating collection {collection_name}...")
        qclient.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
    
    # 3. Load Embedding Model
    print(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
    model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    # 4. Ingest in Batches
    batch_size = 100
    total = len(raw_codes)
    
    for i in range(0, total, batch_size):
        batch = raw_codes[i : i + batch_size]
        texts = [f"{c['code']} {c['description']}" for c in batch]
        
        # Generate embeddings
        embeddings = model.encode(texts)
        
        points = []
        for idx, item in enumerate(batch):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{collection_name}_{item['code']}"))
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embeddings[idx].tolist(),
                    payload={
                        "code": item["code"],
                        "description": item["description"],
                        "type": item["type"]
                    }
                )
            )
            
        qclient.upsert(
            collection_name=collection_name,
            points=points
        )
        print(f"Uploaded batch {i // batch_size + 1}/{(total - 1) // batch_size + 1} ({len(points)} items)")
        
    print("Ingestion completed successfully.")
    
    if langfuse and span:
        try:
            span.end(metadata={"status": "success", "total_records": total})
            langfuse.flush()
        except Exception as e:
            print(f"Failed to end Langfuse trace or flush: {e}")

def run_cli():
    parser = argparse.ArgumentParser(description="Ingest ICD-10 codes into Qdrant.")
    parser.add_argument("--type", choices=["cm", "pcs"], required=True, help="Ingestion type (cm or pcs)")
    args = parser.parse_args()
    
    ingest_codes(args.type)

if __name__ == "__main__":
    run_cli()
