import pydantic


class RAGChunkAndSrc(pydantic.BaseModel):
    chunks: list[str]
    source_id: str = None
    subject: str = "default"


class RAGUpsertResult(pydantic.BaseModel):
    ingested: int
    subject: str


class RAGSearchResult(pydantic.BaseModel):
    contexts: list[str]
    sources: list[str]
    subject: str


class RAQQueryResult(pydantic.BaseModel):
    answer: str
    sources: list[str]
    num_contexts: int
    subject: str