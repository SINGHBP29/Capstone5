# Semantic Deep Flow

This diagram shows the semantic package as it exists now: RCA and fix proposal are scaffolded, while specialist tools exist separately.

```mermaid
flowchart TB
    classDef entry fill:#2f5d62,color:#ffffff,stroke:#23484b,stroke-width:2px;
    classDef wired fill:#eef8f0,color:#14532d,stroke:#4caf50,stroke-width:1px;
    classDef scaffold fill:#fff7ed,color:#7c2d12,stroke:#f59e0b,stroke-dasharray: 5 3;
    classDef branch fill:#f7fbff,color:#1d3557,stroke:#7aa7d9,stroke-width:1px;
    classDef note fill:#f6f4ee,color:#4b5563,stroke:#d9d4c7,stroke-dasharray: 4 3;

    start["Entry: run_semantic_pipeline.py"]:::entry
    rca["Semantic/RootCause/main_agent.py<br/>SemanticRootCauseAgent"]:::scaffold
    specialists["Semantic/RootCause/specialized_agents.py<br/>VectorDBHealthAgent / EmbeddingDriftAgent / SemanticCoverageAgent / SemanticSearchQualityAgent"]:::scaffold
    tools["Specialist tools<br/>vector_db_health / embedding_drift / semantic_coverage / semantic_search_quality"]:::scaffold
    rca_out["RCA output<br/>root_cause would be one of the semantic failure classes"]:::scaffold
    fix["Semantic/Fix_Proposal/fix_agent.py<br/>SemanticFixProposalAgent"]:::scaffold
    eval["Semantic/Eval/eval_agent.py<br/>SemanticEvalAgent"]:::scaffold
    release["Semantic/Release/release_agent.py<br/>SemanticReleaseAgent"]:::wired
    done["End<br/>canary or rollback"]:::entry

    start --> rca --> rca_out --> fix --> eval --> release --> done
    rca -.-> specialists -.-> tools

    subgraph scenario_paths["Likely semantic scenarios"]
        direction LR
        s1["embedding_drift"]:::branch --> s2["EmbeddingDriftTool<br/>compare current vs baseline vectors"]:::scaffold --> s3["recommendation: refresh vectors"]:::scaffold
        s4["index_coverage_gap"]:::branch --> s5["SemanticCoverageTool<br/>compare catalog vs index"]:::scaffold --> s6["recommendation: reindex missing products"]:::scaffold
        s7["vector_db_unreachable"]:::branch --> s8["VectorDBHealthTool<br/>ping DB / check partitions"]:::scaffold --> s9["recommendation: fix platform health first"]:::scaffold
        s10["semantic search quality issue"]:::branch --> s11["SemanticSearchQualityTool"]:::scaffold --> s12["recommendation: refine relevance or query handling"]:::scaffold
    end

    rca_out --> s1
    rca_out --> s4
    rca_out --> s7
    rca_out --> s10

    subgraph fix_paths["Planned fix paths"]
        direction LR
        f1["SemanticFixProposalAgent is scaffolded"]:::scaffold --> f2["Planned tools<br/>vector_refresh / reindex_trigger / semantic_rules"]:::scaffold
    end

    fix --> f1

    subgraph release_path["Release branch"]
        direction LR
        r1{"Decision"}:::wired -->|PROMOTE_TO_CANARY| r2["SemanticCanaryRouterTool"]:::wired
        r1 -->|ROLLBACK_FIX| r3["SemanticRollbackTool"]:::wired
    end

    release --> r1
    r2 --> done
    r3 --> done

    note1["Current state: the semantic package has useful specialist tools, but the main RCA and fix agents are not fully wired yet."]:::note
    note1 -.-> start
```

Reading guide:
- Semantic has the clearest gap between available tools and actual agent wiring.
- The specialist tools can diagnose drift and coverage problems, but the main agents are still scaffolded.
- Release is wired, so once the upstream agents are completed the release step can already operate.
