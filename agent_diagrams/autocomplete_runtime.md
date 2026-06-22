# Autocomplete Runtime Diagram

This diagram follows the current autocomplete modules in the workspace.
The fix agent is present but currently acts as a scaffold, while the evaluation and release layers are wired.

```mermaid
flowchart TD
    start["Autocomplete/RootCause/main_agent.py<br/>AutocompleteRootCauseAgent.main()"] --> rlm["base_agent.py<br/>BaseAgent.run_agent()"]

    rlm --> prefix["Autocomplete/RootCause/Tools/prefix_matching_agent.py<br/>PrefixMatchingAgent"]
    rlm --> pop["Autocomplete/RootCause/Tools/popularity_bias_agent.py<br/>PopularityBiasAgent"]
    rlm --> typo["Autocomplete/RootCause/Tools/typo_tolerance_agent.py<br/>TypoToleranceAgent"]
    prefix --> state1["Autocomplete/state_repository.py"]
    pop --> state2["Autocomplete/state_repository.py"]
    typo --> state3["Autocomplete/state_repository.py"]

    start --> fix["Autocomplete/Fix_Proposal/fix_agent.py<br/>AutocompleteFixProposalAgent"]
    fix -.-> tool1["Autocomplete/Fix_Proposal/Tools/adjust_prefix_weights_tool.py"]
    fix -.-> tool2["Autocomplete/Fix_Proposal/Tools/boost_popular_entities_tool.py"]
    fix -.-> tool3["Autocomplete/Fix_Proposal/Tools/update_typo_dictionary_tool.py"]

    fix --> eval["Autocomplete/Eval/eval_agent.py<br/>AutocompleteEvalAgent"]
    eval --> ctr["Autocomplete/Eval/Tools/evaluate_autocomplete_ctr_tool.py"]
    eval --> diffy["Autocomplete/Eval/Tools/fetch_autocomplete_diffy_report_tool.py"]
    diffy --> state4["Autocomplete/state_repository.py"]

    eval --> release["Autocomplete/Release/release_agent.py<br/>AutocompleteReleaseAgent"]
    release --> canary["Autocomplete/Release/Tools/initiate_autocomplete_canary_tool.py"]
    release --> rollback["Autocomplete/Release/Tools/execute_autocomplete_rollback_tool.py"]

    subgraph success["Success path"]
        start
        rlm
        prefix
        pop
        typo
        state1
        state2
        state3
        fix
        tool1
        tool2
        tool3
        eval
        ctr
        diffy
        state4
        release
        canary
        rollback
    end

    subgraph errors["Error and fallback path"]
        e1["Autocomplete/RootCause/Tools/typo_tolerance_agent.py<br/>No query or no typo match"] --> e2["Root cause candidate stays none"]
        e3["Autocomplete/Eval/Tools/evaluate_autocomplete_ctr_tool.py<br/>Missing baseline_ctr or shadow_ctr"] --> e4["Evaluation returns failed"]
        e5["Autocomplete/Eval/Tools/fetch_autocomplete_diffy_report_tool.py<br/>Diffy API down"] --> e6["Fallback to local state or failed"]
        e7["Autocomplete/Release/release_agent.py<br/>No clear decision"] --> e8["No action needed"]
    end
```

The autocomplete fix tools already exist in `Autocomplete/Fix_Proposal/Tools/`.
They are shown as a dashed link because `Autocomplete/Fix_Proposal/fix_agent.py` has not wired them in yet.

