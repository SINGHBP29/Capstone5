# Catalog Deep Flow

This diagram shows the full working path for catalog issues from signal intake to remediation and release.

```mermaid
flowchart TB
    classDef entry fill:#2f5d62,color:#ffffff,stroke:#23484b,stroke-width:2px;
    classDef wired fill:#eef8f0,color:#14532d,stroke:#4caf50,stroke-width:1px;
    classDef branch fill:#f7fbff,color:#1d3557,stroke:#7aa7d9,stroke-width:1px;
    classDef note fill:#f6f4ee,color:#4b5563,stroke:#d9d4c7,stroke-dasharray: 4 3;

    start["Entry: run_full_pipeline.py<br/>or temporal/activities.py"]:::entry
    rca["Catalog/RootCause/google_agent.py<br/>GoogleRootCauseAgent"]:::wired
    rootcause["Root-cause analysis<br/>catalog_coverage / schema_validation / freshness_check / historical_intent / search_quality / capability_mapping / run_deep_rca_investigation"]:::wired
    rca_out["RCA output<br/>overall_status, root_cause, affected_capabilities, detailed_evidence"]:::wired
    fix["Catalog/Fix_Proposal/fix_agent.py<br/>GoogleFixProposalAgent"]:::wired
    eval["Catalog/Eval/eval_agent.py<br/>GoogleEvalAgent"]:::wired
    release["Catalog/Release/release_agent.py<br/>ReleaseAgent"]:::wired
    done["End<br/>fix promoted or rolled back"]:::entry

    start --> rca --> rootcause --> rca_out --> fix

    subgraph scenario["How RCA maps to fix work"]
        direction LR
        s1["catalog_coverage_gap<br/>missing attributes or missing fields"]:::branch --> t1["llm_inference"]:::wired --> t2["apply_patch"]:::wired --> t3["vector_refresh"]:::wired --> t4["trigger_reindex"]:::wired
        s2["stale_catalog_data<br/>freshness issues"]:::branch --> u1["vector_refresh"]:::wired --> u2["trigger_reindex"]:::wired
        s3["catalog_schema_violation<br/>bad shape or malformed records"]:::branch --> v1["apply_patch"]:::wired --> v2["vector_refresh"]:::wired --> v3["trigger_reindex"]:::wired
        s4["low_search_relevance / embedding_failure"]:::branch --> w1["map_semantic_intent"]:::wired --> w2["apply_semantic_rules"]:::wired --> w3["apply_synonyms"]:::wired
        s5["missing_catalog_entity<br/>needs deeper forensic analysis"]:::branch --> x1["run_deep_rca_investigation"]:::wired
    end

    fix --> t1
    fix --> u1
    fix --> v1
    fix --> w1
    fix --> x1

    fix --> fix_out["Fix output<br/>actions_taken, summary"]:::wired --> eval

    subgraph evaluation["Evaluation branch"]
        direction LR
        e1["DiffyApiTool<br/>fetch_diffy_report"]:::wired --> e2["MetricsEvaluatorTool<br/>evaluate_metrics"]:::wired --> e3{"NDCG improved?"}:::branch
    end

    eval --> e1
    e3 -->|yes| release
    e3 -->|no| release

    subgraph release_path["Release branch"]
        direction LR
        r1{"Decision from eval"}:::branch -->|PROMOTE_TO_CANARY| r2["CanaryRouterTool<br/>initiate_canary_release"]:::wired
        r1 -->|ROLLBACK_FIX| r3["RollbackTool<br/>execute_rollback"]:::wired
    end

    release --> r1
    r2 --> done
    r3 --> done

    note1["Files that execute this path directly:<br/>Catalog/RootCause/google_agent.py<br/>Catalog/Fix_Proposal/fix_agent.py<br/>Catalog/Eval/eval_agent.py<br/>Catalog/Release/release_agent.py"]:::note
    note1 -.-> start
```

Reading guide:
- RCA decides which catalog problem class you are in.
- Fix proposal then chooses the matching remediation tools.
- Evaluation checks whether the fix improved the shadow search results.
- Release either promotes the fix or rolls it back.

