# Temporal Runtime Diagram

This diagram shows the current Temporal wiring in two layers:
- the direct workflow layer in `temporal/workflows.py` and `temporal/activities.py`
- the ADK layer in `temporal/catalog_workflows.py`, `temporal/agents.py`, and `temporal/catalog_activities.py`

```mermaid
flowchart TD
    subgraph launchers["Launchers and workers"]
        l1["temporal/run_worker.py<br/>worker for UnifiedSearchAiRepairWorkflow"]
        l2["temporal/worker.py<br/>legacy worker wrapper"]
        l3["temporal/run_unified_workflow.py<br/>client launcher"]
        l4["temporal/run_semantic_workflow.py<br/>client launcher"]
        l5["temporal/cat_start_workflow.py<br/>client launcher"]
        l6["temporal/catalog_worker.py<br/>worker for AdkSearchOpsWorkflow"]
    end

    subgraph direct["Direct workflow layer"]
        l1 --> w1["temporal/workflows.py<br/>UnifiedSearchAiRepairWorkflow"]
        l2 --> w1
        l3 --> w1
        l4 -.-> e_sem["temporal/workflows.py<br/>SemanticAiRepairWorkflow is currently broken"]

        w1 --> d1{"signal.type"}
        d1 -->|catalog| a1["temporal/activities.py<br/>root_cause_activity"]
        d1 -->|autocomplete| a2["temporal/activities.py<br/>autocomplete_root_cause_activity"]
        d1 -->|semantic| e_sem

        a1 --> cat1["Catalog/RootCause/google_agent.py<br/>GoogleRootCauseAgent"]
        a1 --> cat2["Catalog/Fix_Proposal/fix_agent.py<br/>GoogleFixProposalAgent"]
        a2 --> auto1["Autocomplete/RootCause/main_agent.py<br/>AutocompleteRootCauseAgent"]
        a2 --> auto2["Autocomplete/Fix_Proposal/fix_agent.py<br/>AutocompleteFixProposalAgent"]

        w1 --> eval1["temporal/activities.py<br/>eval_activity"]
        eval1 --> evalagent["Catalog/Eval/eval_agent.py<br/>GoogleEvalAgent"]
        eval1 --> ndcg{"NDCG < 0.84?"}
        ndcg -->|yes| approval["temporal/signal_workflow.py / temporal/approval_tool.py<br/>approve_deployment signal"]
        ndcg -->|no| release1["temporal/activities.py<br/>release_activity"]
        approval --> release1
        release1 --> releaseagent["Release/release_agent.py<br/>ReleaseAgent"]
    end

    subgraph adk["ADK workflow layer"]
        l6 --> w2["temporal/catalog_workflows.py<br/>AdkSearchOpsWorkflow"]
        l5 --> w2

        w2 --> helper["temporal/catalog_workflows.py<br/>_run_agent_in_workflow()"]
        helper --> adk_agents["temporal/agents.py<br/>rca_agent / fix_agent / eval_agent / release_agent"]
        adk_agents --> adk_acts["temporal/catalog_activities.py<br/>catalog_coverage / schema_validation / apply_patch / vector_refresh / fetch_diffy_report / evaluate_metrics / initiate_canary_release / execute_rollback"]
        adk_acts --> adk_tools["Catalog/* tool classes"]
        helper --> hb["temporal/shared.py<br/>HeartbeatingStream"]
    end

    subgraph errors["Error and legacy drift"]
        e1["temporal/workflows.py<br/>unknown signal.type"] --> e2["ValueError"]
        e3["temporal/workflows.py<br/>semantic activity imports missing"] --> e4["Semantic branch cannot complete as written"]
        e5["temporal/run_autocomplete_workflow.py<br/>imports AutocompleteAiRepairWorkflow that does not exist"] --> e6["Stale launcher"]
        e7["temporal/run_workflow.py<br/>imports SearchAiRepairWorkflow that does not exist"] --> e8["Stale launcher"]
        e9["temporal/catalog_workflow.py<br/>references run_root_cause_agent that is not defined in catalog_activities.py"] --> e10["Legacy path only"]
    end
```

The active Temporal catalog flow uses `UnifiedSearchAiRepairWorkflow` plus the ADK workflow `AdkSearchOpsWorkflow`.
The semantic and autocomplete launcher files are present, but the workflow imports are currently stale.
