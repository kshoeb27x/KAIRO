from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from importlib import import_module


Database = import_module(
    "03_DATA.Database.database"
).Database

KnowledgeStore = import_module(
    "03_DATA.Knowledge.knowledge_store"
).KnowledgeStore

VectorStore = import_module(
    "03_DATA.Vector.vector_store"
).VectorStore

RAGRetriever = import_module(
    "03_DATA.RAG.retriever"
).RAGRetriever

DataPipeline = import_module(
    "03_DATA.Pipelines.pipeline"
).DataPipeline

DataManager = import_module(
    "03_DATA.Data_Management.data_manager"
).DataManager


def test_database():

    database = Database()

    database.insert(
        "users",
        "one",
        {
            "name": "KAIRO"
        },
    )

    result = database.get(
        "users",
        "one",
    )

    assert result["name"] == "KAIRO"

    assert database.health()["records"] == 1


def test_knowledge():

    knowledge = KnowledgeStore()

    knowledge.add(
        "one",
        "KAIRO",
        "KAIRO is an AI operating system.",
    )

    results = knowledge.search(
        "AI operating system"
    )

    assert len(results) == 1
    assert results[0].item_id == "one"


def test_vector():

    vectors = VectorStore()

    vectors.add(
        "one",
        [1.0, 0.0],
        {"name": "first"},
    )

    vectors.add(
        "two",
        [0.0, 1.0],
        {"name": "second"},
    )

    results = vectors.search(
        [1.0, 0.0],
        limit=1,
    )

    assert len(results) == 1
    assert results[0]["vector_id"] == "one"


def test_rag():

    knowledge = KnowledgeStore()

    vectors = VectorStore()

    knowledge.add(
        "one",
        "Trading",
        "Market structure and liquidity.",
    )

    vectors.add(
        "one",
        [1.0, 0.0],
    )

    rag = RAGRetriever(
        knowledge,
        vectors,
    )

    text_results = rag.retrieve_text(
        "liquidity"
    )

    vector_results = rag.retrieve_vector(
        [1.0, 0.0]
    )

    assert len(text_results) == 1
    assert len(vector_results) == 1


def test_pipeline():

    pipeline = DataPipeline(
        "test"
    )

    pipeline.add_step(
        lambda value: value + 1
    )

    pipeline.add_step(
        lambda value: value * 2
    )

    result = pipeline.run(2)

    assert result.status == "COMPLETED"
    assert result.output == 6


def test_data_manager():

    database = Database()
    knowledge = KnowledgeStore()
    vectors = VectorStore()

    manager = DataManager(
        database,
        knowledge,
        vectors,
    )

    health = manager.health()

    assert health["status"] == "ONLINE"
    assert health["database"]["status"] == "ONLINE"
    assert health["knowledge"]["status"] == "ONLINE"
    assert health["vector"]["status"] == "ONLINE"
