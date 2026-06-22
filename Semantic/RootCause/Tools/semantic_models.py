"""Canonical data models for the semantic index pipeline."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class EmbeddingRecord:
    """A single embedding vector for a product in the semantic index."""
    sku: str
    vector: List[float]
    indexed_at: str  # ISO-8601 UTC
    model_version: str
    dimension: int


@dataclass(frozen=True)
class IndexPartition:
    """A partition in the vector DB (e.g. LanceDB version)."""
    partition_id: str
    created_at: str  # ISO-8601 UTC
    vector_count: int
    status: str       # "active" | "stale" | "rebuilding"


@dataclass
class EmbeddingDriftResult:
    """Result of comparing baseline vs current embeddings for drift."""
    tool_name: str
    status: str
    total_products_compared: int
    drifted_products: int
    max_cosine_distance: float
    avg_cosine_distance: float
    root_cause_candidate: str
    evidence: List[str]


@dataclass
class SemanticCoverageResult:
    """Result of checking semantic index coverage."""
    tool_name: str
    status: str
    catalog_count: int
    indexed_count: int
    missing_from_index: int
    stale_embeddings: int
    coverage_percent: float
    root_cause_candidate: str
    evidence: List[str]


@dataclass
class VectorDBHealthResult:
    """Result of vector DB health check."""
    tool_name: str
    status: str
    reachable: bool
    latency_ms: float
    total_vectors: int
    total_partitions: int
    stale_partitions: int
    index_version: str
    root_cause_candidate: str
    evidence: List[str]


@dataclass
class SemanticSearchQualityResult:
    """Result of evaluating actual semantic search quality for a query."""
    tool_name: str
    status: str
    query: str
    total_results: int
    zero_result: bool
    avg_score: float
    top_sku: Optional[str]
    root_cause_candidate: str
    evidence: List[str]


@dataclass
class SemanticCapabilityMappingResult:
    """Result of mapping semantic index issues to affected capabilities."""
    tool_name: str
    status: str
    affected_capabilities: List[str]
    root_cause_candidate: str
    evidence: List[str]


@dataclass
class FullSemanticHealthResult:
    """Aggregated health result covering all semantic index dimensions."""
    overall_status: str
    vector_db_status: str
    embedding_drift_status: str
    coverage_status: str
    search_quality_status: str
    root_cause: str
    affected_capabilities: List[str]
    summary: str
    detailed_evidence: List[str]
    executed_tools: List[str] = field(default_factory=list)
