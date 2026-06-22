# Catalog Agent Variants

The catalog package contains several working RCA implementations.
This diagram shows the main variants and where they live.

```mermaid
flowchart TD
    subgraph langchain["LangChain ReAct variant"]
        m1["Catalog/RootCause/main_agent.py<br/>RootCauseAgent"]
        m1 --> m2["langchain.agents.executors.AgentExecutor"]
        m2 --> m3["Catalog/RootCause/Tools/*"]
    end

    subgraph google["BaseAgent + tool wrappers"]
        g1["Catalog/RootCause/google_agent.py<br/>GoogleRootCauseAgent"]
        g1 --> g2["base_agent.py<br/>BaseAgent.run_agent()"]
        g2 --> g3["Catalog/RootCause/Tools/*"]
    end

    subgraph fastpath["Standalone fast-rlm demo"]
        f1["Catalog/RootCause/fast_rlm_agent.py<br/>Standalone main()"]
        f1 --> f2["tool_catalog_coverage / tool_schema_validation / tool_freshness_check"]
        f1 --> f3["tool_historical_intent / tool_search_quality / tool_capability_mapping"]
    end

    subgraph magellan["FastRLM runbook variant"]
        mg1["Catalog/RootCause/magellan_agent.py<br/>MagellanFastRLMOpsAgent"]
        mg1 --> mg2["fast_rlm + rlm_sub_query"]
        mg1 --> mg3["Catalog/RootCause/Tools/catalog_coverage_tool.py"]
        mg1 --> mg4["Catalog/RootCause/Tools/schema_validation.py"]
        mg1 --> mg5["Catalog/RootCause/Tools/freshness.py"]
        mg1 --> mg6["Catalog/RootCause/Tools/historical_intent.py"]
        mg1 --> mg7["Catalog/RootCause/Tools/search_Quality.py"]
        mg1 --> mg8["Catalog/RootCause/Tools/capability_mapping_tools.py"]
        mg1 --> mg9["Catalog/RootCause/Tools/vector_sync.py"]
    end

    subgraph adk["ADK variant"]
        a1["Catalog/RootCause/specialized_agents.py<br/>RootCauseAgent / CatalogHealthAgent"]
        a1 --> a2["BaseGoogleADKAgent"]
        a1 --> a3["Catalog/RootCause/Tools/catalog_coverage_tool.py"]
        a1 --> a4["Catalog/RootCause/Tools/schema_validation.py"]
        a1 --> a5["Catalog/RootCause/Tools/freshness.py"]
        a1 --> a6["Catalog/RootCause/Tools/historical_intent.py"]
        a1 --> a7["Catalog/RootCause/Tools/search_Quality.py"]
        a1 --> a8["Catalog/RootCause/Tools/capability_mapping_tools.py"]
        a1 --> a9["Catalog/RootCause/Tools/embedding.py"]
        a1 --> a10["Catalog/RootCause/Tools/vector_sync.py"]
        a1 --> a11["Catalog/RootCause/Tools/query_intent.py"]
        a1 --> a12["Catalog/RootCause/Tools/index.py"]
    end

```

Current usage notes:
- `Catalog/RootCause/google_agent.py` is the catalog RCA module used by `temporal/activities.py`.
- `Catalog/RootCause/specialized_agents.py` is the standalone ADK demo variant.
- `Catalog/RootCause/fast_rlm_agent.py` and `Catalog/RootCause/magellan_agent.py` are separate fast-RLM examples.
- The main graph is a map of variants, not a strict runtime sequence.
