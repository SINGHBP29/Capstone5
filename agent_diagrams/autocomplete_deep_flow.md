# Autocomplete Deep Flow

This diagram shows the autocomplete RCA path and the current fix/eval/release working state.

```mermaid
flowchart TB
    classDef entry fill:#2f5d62,color:#ffffff,stroke:#23484b,stroke-width:2px;
    classDef wired fill:#eef8f0,color:#14532d,stroke:#4caf50,stroke-width:1px;
    classDef scaffold fill:#fff7ed,color:#7c2d12,stroke:#f59e0b,stroke-dasharray: 5 3;
    classDef branch fill:#f7fbff,color:#1d3557,stroke:#7aa7d9,stroke-width:1px;
    classDef note fill:#f6f4ee,color:#4b5563,stroke:#d9d4c7,stroke-dasharray: 4 3;

    start["Entry: run_autocomplete_pipeline.py"]:::entry
    rca["Autocomplete/RootCause/main_agent.py<br/>AutocompleteRootCauseAgent"]:::wired
    rootcause["RCA tools<br/>run_prefix_matching_analysis / run_popularity_bias_analysis / run_typo_tolerance_analysis / run_deep_rca_investigation"]:::wired
    rca_out["RCA output<br/>root_cause, summary, detailed_evidence, executed_tools"]:::wired
    fix["Autocomplete/Fix_Proposal/fix_agent.py<br/>AutocompleteFixProposalAgent"]:::scaffold
    eval["Autocomplete/Eval/eval_agent.py<br/>AutocompleteEvalAgent"]:::wired
    release["Autocomplete/Release/release_agent.py<br/>AutocompleteReleaseAgent"]:::wired
    done["End<br/>canary or rollback"]:::entry

    start --> rca --> rootcause --> rca_out --> fix --> eval --> release --> done

    subgraph rcabranches["Scenario to root cause mapping"]
        direction LR
        a1["prefix_index_stale"]:::wired --> a2["PrefixMatchingAgent<br/>reads AutocompleteStateRepository"]:::wired --> a3["recommendation: adjust_prefix_weights"]:::wired
        b1["popularity_bias_low"]:::wired --> b2["PopularityBiasAgent<br/>reads AutocompleteStateRepository"]:::wired --> b3["recommendation: boost_popular_entities"]:::wired
        c1["missing_typo_synonyms"]:::wired --> c2["TypoToleranceAgent<br/>reads AutocompleteStateRepository"]:::wired --> c3["recommendation: update_typo_dictionary"]:::wired
    end

    rca_out --> a1
    rca_out --> b1
    rca_out --> c1

    subgraph fixbranch["Current fix proposal status"]
        direction LR
        f1["AutocompleteFixProposalAgent is scaffolded"]:::scaffold --> f2["Planned tools<br/>adjust_prefix_weights / boost_popular_entities / update_typo_dictionary"]:::scaffold
    end

    fix --> f1

    subgraph evaluation["Evaluation branch"]
        direction LR
        e1["evaluate_autocomplete_ctr_tool"]:::wired --> e2["fetch_autocomplete_diffy_report_tool"]:::wired --> e3{"metrics / diffy say promote?"}:::wired
    end

    eval --> e1
    e3 -->|PROMOTE_TO_CANARY| release
    e3 -->|ROLLBACK_FIX| release

    subgraph release_path["Release branch"]
        direction LR
        r1{"Decision"}:::wired -->|PROMOTE_TO_CANARY| r2["initiate_autocomplete_canary"]:::wired
        r1 -->|ROLLBACK_FIX| r3["execute_autocomplete_rollback"]:::wired
    end

    release --> r1
    r2 --> done
    r3 --> done

    note1["Direct files: Autocomplete/RootCause/main_agent.py, Autocomplete/Eval/eval_agent.py, Autocomplete/Release/release_agent.py"]:::note
    note1 -.-> start
```

Reading guide:
- RCA is working and selects between prefix, popularity, and typo causes.
- Fix proposal exists as a class, but the actual fix tools are still commented out.
- Evaluation and release are wired and already choose promote vs rollback.
