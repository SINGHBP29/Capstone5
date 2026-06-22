# Semantic Runtime Diagram

The semantic package currently has scaffolded agent shells plus standalone specialist tools.
This diagram reflects the current code exactly.

```mermaid
flowchart TD
    start["Semantic/RootCause/main_agent.py<br/>SemanticRootCauseAgent"] --> rca["base_agent.py<br/>BaseAgent.run_agent()"]
    rca -.-> stub1["No tool registration yet"]
    rca -.-> stub2["run_deep_rca_investigation available through BaseAgent"]

    specialists["Semantic/RootCause/specialized_agents.py<br/>VectorDBHealthAgent / EmbeddingDriftAgent / SemanticCoverageAgent / SemanticSearchQualityAgent"]
    specialists -.-> s1["Semantic/RootCause/Tools/vector_db_health.py"]
    specialists -.-> s2["Semantic/RootCause/Tools/embedding_drift.py"]
    specialists -.-> s3["Semantic/RootCause/Tools/semantic_coverage.py"]
    specialists -.-> s4["Semantic/RootCause/Tools/semantic_search_quality.py"]

    fix["Semantic/Fix_Proposal/fix_agent.py<br/>SemanticFixProposalAgent"] -.-> f1["Semantic/Fix_Proposal/Tools/vector_refresh_tool.py"]
    fix -.-> f2["Semantic/Fix_Proposal/Tools/reindex_trigger_tool.py"]
    fix -.-> f3["Semantic/Fix_Proposal/Tools/semantic_rules_tool.py"]

    eval["Semantic/Eval/eval_agent.py<br/>SemanticEvalAgent"] -.-> e1["No tool registration yet"]

    release["Semantic/Release/release_agent.py<br/>SemanticReleaseAgent"]
    release --> c1["Semantic/Release/Tools/canary_router_tool.py"]
    release --> c2["Semantic/Release/Tools/rollback_tool.py"]

    start --> fix
    fix --> eval
    eval --> release

    subgraph success["Success path"]
        start
        rca
        specialists
        s1
        s2
        s3
        s4
        fix
        f1
        f2
        f3
        eval
        release
        c1
        c2
    end

    subgraph errors["Error and placeholder path"]
        e3["Semantic/RootCause/main_agent.py<br/>Agent remains a scaffold until tools are registered"] --> e4["Output is mostly generic BaseAgent behavior"]
        e5["Semantic/Eval/eval_agent.py<br/>No evaluation tools wired"] --> e6["Evaluation is effectively a placeholder"]
        e7["Semantic/Fix_Proposal/fix_agent.py<br/>No remediation tools wired"] --> e8["Fix step is effectively a placeholder"]
    end
```

The standalone specialist tools under `Semantic/RootCause/Tools/` are currently available, but the main semantic agent does not wire them in yet.

