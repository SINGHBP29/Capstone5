from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class VerificationCheck:
    name: str
    passed: bool
    details: str

@dataclass
class VerificationReport:
    all_passed: bool
    checks: List[VerificationCheck] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

@dataclass
class MetricDelta:
    before: Any
    after: Any
    delta: Any

@dataclass
class MetricsReport:
    zero_result_rate: MetricDelta
    ctr: MetricDelta
    latency_p95_ms: MetricDelta
    relevance_score: MetricDelta
    raw_metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DecisionReport:
    action: str  # PROMOTE | ROLLBACK | HOLD
    confidence: float
    reason: str
    next_traffic_tier: str

@dataclass
class ThresholdUpdatesReport:
    watchlist_added: Optional[str] = None
    monitoring_window: str = "7d"
    regression_threshold: str = "zero_result_rate > 0.05"
    runbook_template_patched: bool = False
    signal_sensitivity_adjusted: List[str] = field(default_factory=list)

@dataclass
class AuditRecord:
    incident_id: str
    gap_type: str
    fix_order_executed: int
    patches_applied: int
    evidence_artifacts: int
    owner_path: str
    rollback_available: bool

@dataclass
class FeedbackResult:
    agent: str = "FeedbackAgent"
    status: str = "ok"
    query: str = ""
    timestamp: str = ""
    verification: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    threshold_updates: Optional[Dict[str, Any]] = None
    audit_record: Optional[Dict[str, Any]] = None

@dataclass
class CanaryTierResult:
    tier_percent: int
    feedback_decision: str   # PROMOTE | ROLLBACK | HOLD
    confidence: float
    reason: str
    metrics_snapshot: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

@dataclass
class CanaryState:
    incident_id: str
    query: str
    status: str = "PENDING"           # PENDING | IN_PROGRESS | COMPLETED | ROLLED_BACK | HELD
    current_tier: int = 0
    tiers_completed: List[int] = field(default_factory=list)
    tier_results: List[CanaryTierResult] = field(default_factory=list)
    hold_count: int = 0
    final_decision: str = ""

