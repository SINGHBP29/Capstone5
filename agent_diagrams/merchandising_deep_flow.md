# Merchandising Deep Flow

This diagram shows the full working merchandising path, including the Fast-RLM fix router.

```mermaid
flowchart TB
    classDef entry fill:#2f5d62,color:#ffffff,stroke:#23484b,stroke-width:2px;
    classDef wired fill:#eef8f0,color:#14532d,stroke:#4caf50,stroke-width:1px;
    classDef branch fill:#f7fbff,color:#1d3557,stroke:#7aa7d9,stroke-width:1px;
    classDef note fill:#f6f4ee,color:#4b5563,stroke:#d9d4c7,stroke-dasharray: 4 3;

    start["Entry: run_merchandising_pipeline.py"]:::entry
    rca["Merchandising/RootCause/main_agent.py<br/>MerchandisingRootCauseAgent"]:::wired
    rootcause["RCA tools<br/>check_rule_priority_conflict / check_rule_scope_overlap / check_stale_rules / run_deep_rca_investigation"]:::wired
    rca_out["RCA output<br/>root_cause = rule_priority_conflict | rule_scope_overlap | stale_expired_rules"]:::wired
    fix["Merchandising/Fix_Proposal/fix_agent.py<br/>MerchandisingFixAgent"]:::wired
    eval["Merchandising/Eval/eval_agent.py<br/>MerchandisingEvalAgent"]:::wired
    release["Merchandising/Release/release_agent.py<br/>MerchandisingReleaseAgent"]:::wired
    done["End<br/>canary or rollback"]:::entry

    start --> rca --> rootcause --> rca_out --> fix --> eval --> release --> done

    subgraph rootcause_paths["How each merchandising RCA works"]
        direction LR
        p1["rule_priority_conflict"]:::branch --> p2["RulePriorityConflictAgent<br/>loads MerchandisingStateRepository"]:::wired --> p3["best active scope has opposing actions"]:::wired
        o1["rule_scope_overlap"]:::branch --> o2["RuleOverlapAgent<br/>loads MerchandisingStateRepository"]:::wired --> o3["multiple active rules intersect the same scope"]:::wired
        s1["stale_expired_rules"]:::branch --> s2["StaleRuleAgent<br/>loads MerchandisingStateRepository"]:::wired --> s3["expired or stale rules are still active"]:::wired
    end

    rca_out --> p1
    rca_out --> o1
    rca_out --> s1

    subgraph fix_router["Fast-RLM fix routing"]
        direction LR
        f1["MerchandisingFixAgent.fast_rlm()"]:::wired --> f2{"route root cause"}:::branch
        f2 -->|rule_priority_conflict| f3["resolve_priority"]:::wired
        f2 -->|stale_expired_rules| f4["deactivate_conflicting_rules"]:::wired
        f2 -->|rule_scope_overlap| f5["merge_overlapping_rules"]:::wired
        f3 --> f6["asyncio.gather executes selected tools"]:::wired
        f4 --> f6
        f5 --> f6
    end

    fix --> f1

    subgraph evaluation["Evaluation branch"]
        direction LR
        e1["validate_rule_consistency"]:::wired --> e2["fetch_merchandising_regression_report"]:::wired --> e3{"conflicts_remaining == 0 and regressions_found == 0?"}:::branch
    end

    eval --> e1
    e3 -->|yes| release
    e3 -->|no| release

    subgraph release_path["Release branch"]
        direction LR
        r1{"Decision"}:::branch -->|PROMOTE_TO_CANARY| r2["initiate_merchandising_canary"]:::wired
        r1 -->|ROLLBACK_FIX| r3["execute_merchandising_rollback"]:::wired
    end

    release --> r1
    r2 --> done
    r3 --> done

    note1["Direct files: Merchandising/RootCause/main_agent.py, Merchandising/Fix_Proposal/fix_agent.py, Merchandising/Eval/eval_agent.py, Merchandising/Release/release_agent.py"]:::note
    note1 -.-> start
```

Reading guide:
- RCA chooses between conflicting rules, overlapping scopes, and stale rules.
- Fix proposal is the most dynamic part here because it uses Fast-RLM to route to the exact remediation tools.
- Evaluation checks consistency and regression safety before release.

