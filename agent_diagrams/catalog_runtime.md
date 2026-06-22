# Catalog Runtime Diagram

This diagram follows the current catalog execution path used by the source files in this workspace.

```mermaid
flowchart TD
    start["Catalog/RootCause/google_agent.py<br/>GoogleRootCauseAgent.main()"] --> rlm["base_agent.py<br/>BaseAgent.run_agent()"]

    rlm --> cov["Catalog/RootCause/Tools/catalog_coverage_tool.py<br/>CatalogCoverageTool"]
    rlm --> sch["Catalog/RootCause/Tools/schema_validation.py<br/>CatalogSchemaValidationTool"]
    rlm --> fresh["Catalog/RootCause/Tools/freshness.py<br/>CatalogFreshnessTool"]
    rlm --> hist["Catalog/RootCause/Tools/historical_intent.py<br/>CatalogHistoricalIntentTool"]
    rlm --> qual["Catalog/RootCause/Tools/search_Quality.py<br/>CatalogSearchQualityTool"]
    rlm --> cap["Catalog/RootCause/Tools/capability_mapping_tools.py<br/>CatalogCapabilityMappingTool"]
    rlm --> deep["base_agent.py<br/>run_deep_rca_investigation"]

    start --> fix["Catalog/Fix_Proposal/fix_agent.py<br/>GoogleFixProposalAgent"]
    fix --> inf["Catalog/Fix_Proposal/Tools/llm_inference_tool.py<br/>LLMInferenceTool"]
    fix --> patch["Catalog/Fix_Proposal/Tools/patch_apply_tool.py<br/>PatchApplyTool"]
    fix --> vector["Catalog/Fix_Proposal/Tools/vector_refresh_tool.py<br/>VectorRefreshTool"]
    fix --> reindex["Catalog/Fix_Proposal/Tools/reindex_trigger_tool.py<br/>ReindexTriggerTool"]
    fix --> syn1["Catalog/Fix_Proposal/Tools/synonym_generator_tool.py<br/>SynonymGeneratorTool"]
    fix --> syn2["Catalog/Fix_Proposal/Tools/synonym_apply_tool.py<br/>SynonymApplyTool"]
    fix --> sem1["Catalog/Fix_Proposal/Tools/semantic_intent_tool.py<br/>SemanticIntentMappingTool"]
    fix --> sem2["Catalog/Fix_Proposal/Tools/semantic_rules_tool.py<br/>SemanticRulesTool"]

    fix --> eval["Catalog/Eval/eval_agent.py<br/>GoogleEvalAgent"]
    eval --> diffy["Catalog/Eval/Tools/diffy_api_tool.py<br/>DiffyApiTool"]
    diffy --> metrics["Catalog/Eval/Tools/metrics_evaluator_tool.py<br/>MetricsEvaluatorTool"]

    eval --> release["Catalog/Release/release_agent.py<br/>ReleaseAgent"]
    release --> canary["Catalog/Release/Tools/canary_router_tool.py<br/>CanaryRouterTool"]
    release --> rollback["Catalog/Release/Tools/rollback_tool.py<br/>RollbackTool"]

    subgraph success["Success path"]
        start
        rlm
        cov
        sch
        fresh
        hist
        qual
        cap
        deep
        fix
        inf
        patch
        vector
        reindex
        syn1
        syn2
        sem1
        sem2
        eval
        diffy
        metrics
        release
        canary
        rollback
    end

    subgraph errors["Error and fallback path"]
        e1["base_agent.py<br/>Missing GOOGLE_API_KEY or Vertex token"] --> e2["RCA returns status=ERROR"]
        e3["base_agent.py<br/>run_deep_rca_investigation auth failure"] --> e4["Deep RCA returns Authentication Error"]
        e5["Catalog/Eval/Tools/diffy_api_tool.py<br/>No diff_id, API failure, or fallback failure"] --> e6["Eval returns failed"]
        e7["Catalog/Eval/Tools/metrics_evaluator_tool.py<br/>No execution_results"] --> e8["Metrics evaluation failed"]
        e9["Catalog/Release/release_agent.py<br/>Decision is neither PROMOTE_TO_CANARY nor ROLLBACK_FIX"] --> e10["No action needed"]
    end
```

The catalog release step uses `Catalog/Release/release_agent.py` in the direct pipeline.
The Temporal path uses a different release agent in `Release/release_agent.py`.

