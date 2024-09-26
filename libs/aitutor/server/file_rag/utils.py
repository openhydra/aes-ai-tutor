from aitutor.server.file_rag.retrievers import (
    BaseRetrieverService,
    EnsembleRetrieverService,
    MilvusVectorstoreRetrieverService,
    VectorstoreRetrieverService,
)

Retrivals = {
    "milvusvectorstore": MilvusVectorstoreRetrieverService,
    "vectorstore": VectorstoreRetrieverService,
    "ensemble": EnsembleRetrieverService,
}


def get_Retriever(type: str = "vectorstore") -> BaseRetrieverService:
    return Retrivals[type]
