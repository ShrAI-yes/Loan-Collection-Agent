from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.document_loaders import PyPDFDirectoryLoader: deprecated
from langchain_community.document_loaders import PyPDFDirectoryLoader
import chromadb
from chromadb.utils import embedding_functions
import uuid

def load_dir(dir='./vector_db/'):
    loader = PyPDFDirectoryLoader(dir)
    documents = loader.load()
    return documents

def chunking(documents):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=20,separators=["\n\n", "\n", " ", ""])
    chunks = text_splitter.split_documents(documents)
    ids = [str(uuid.uuid1()) for _ in range(len(chunks))]
    texts = [chunk.page_content for chunk in chunks]
    metadata = [chunk.metadata for chunk in chunks]
    return ids, texts, metadata

def embed_chunks(ids, chunks, metadata) -> None:
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

def fetch_query(query):
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")
    client = chromadb.PersistentClient(path="./vector_db/")
    collection = client.get_or_create_collection(
        name='policies',
        embedding_function=embedding_function
    )

    results = collection.query(
        query_texts=[query],
        n_results=3,
        include=["documents", "metadatas"]
    )

    context = ''.join([rules for rules in results['documents'][0]])
    return context
