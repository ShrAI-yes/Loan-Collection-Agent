from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFDirectoryLoader
import chromadb
from chromadb.utils import embedding_functions
import uuid
import os

def load_dir(dir="./vector_db/"):
    print(f"Debug: Checking directory {dir}")
    if not os.path.exists(dir):
        print(f"Debug: Directory {dir} does not exist")
        return []
    files = os.listdir(dir)
    print(f"Debug: Files in {dir}: {files}")
    loader = PyPDFDirectoryLoader(dir)
    documents = loader.load()
    print(f"Debug: Loaded {len(documents)} documents from {dir}")
    return documents

def chunking(documents):
    if not documents:
        print("Debug: No documents to chunk")
        return [], [], []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=20, separators=["\n\n", "\n", " ", ""])
    chunks = text_splitter.split_documents(documents)
    ids = [str(uuid.uuid1()) for _ in range(len(chunks))]
    texts = [chunk.page_content for chunk in chunks]
    metadata = [chunk.metadata for chunk in chunks]
    print(f"Debug: Created {len(chunks)} chunks")
    return ids, texts, metadata

def embed_chunks(ids, chunks, metadata) -> None:
    if not chunks:
        print("Debug: No chunks to embed")
        return
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")
    client = chromadb.PersistentClient(path="./vector_db/")
    collection = client.get_or_create_collection(
        name='policies',
        embedding_function=embedding_function
    )
    collection.add(
        documents=chunks,
        metadatas=metadata,
        ids=ids
    )
    print(f"Debug: Embedded {len(chunks)} chunks into 'policies' collection")

def fetch_query(query):
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")
    client = chromadb.PersistentClient(path="./vector_db/")
    collection = client.get_or_create_collection(
        name='policies',
        embedding_function=embedding_function
    )
    print(f"Debug: Querying collection with {collection.count()} documents")
    results = collection.query(
        query_texts=[query],
        n_results=3,
        include=["documents", "metadatas"]
    )
    print(f"Debug: Query '{query}' returned results: {results}")
    if not results['documents'] or not results['documents'][0]:
        print("Debug: No documents found for query")
        return "मुझे वह जानकारी नहीं मिल सकी। कृपया अपनी लोन नीतियाँ जाँचें।"
    context = ' '.join([rules for rules in results['documents'][0]])
    # Simple refinement: extract key sentence or truncate
    if "default" in query.lower() or "नहीं" in query:
        if "recovery of dues" in context:
            return "अगर आप भुगतान नहीं करते, तो बैंक डिफॉल्ट में देय राशि की वसूली के लिए कदम उठाएगा।"
    if "early" in query.lower() or "जल्दी" in query:
        if "Loan closures" in context:
            return "लोन जल्दी बंद करने पर यह वेवर डेलिगेशन मैट्रिक्स के अनुसार होगा।"
    print(f"Debug: Retrieved context: {context}")
    return context[:200] + "..." if len(context) > 200 else context  # Truncate for brevity

if __name__ == "__main__":
    docs = load_dir('./RAG docs/')
    ids, texts, metadata = chunking(docs)
    embed_chunks(ids, texts, metadata)
    result = fetch_query('All policies related to loan')
    print(f"Test result: {result}")