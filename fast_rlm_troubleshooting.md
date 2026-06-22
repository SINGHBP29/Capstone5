# Troubleshooting `fast-rlm` Errors

This document outlines common errors encountered while working with the `fast-rlm` library and provides their solutions.

---

### 1. `tools must be callables, got str`

**Symptoms:**
The agent fails with a `TypeError`, indicating that the `fast_rlm.run` function expected a callable object (like a function) but received a string instead.

**Root Cause:**
This error occurs when you pass a dictionary of tools to the `tools` parameter of the `fast_rlm.run` function. The library iterates over the dictionary's keys, which are the string names of the tools, instead of the actual function objects.

**Solution:**
To resolve this, you must provide a list of the actual tool functions. If your tools are stored in a dictionary (e.g., `self._tool_functions`), you can easily create this list by passing the dictionary's values.

**Example:**
```python
# Incorrect: Passing a dictionary of tools
# response = await asyncio.to_thread(
#     fast_rlm.run,
#     query_prompt,
#     config=self.rlm_config,
#     tools=self._tool_functions,  # This is a dictionary
#     verbose=True,
# )

# Correct: Passing a list of tool functions
response = await asyncio.to_thread(
    fast_rlm.run,
    query_prompt,
    config=self.rlm_config,
    tools=list(self._tool_functions.values()),  # Pass the functions
    verbose=True,
)
```

---

### 2. `run() got an unexpected keyword argument '__tools__'`

**Symptoms:**
The agent fails with a `TypeError`, stating that the `fast_rlm.run` function received an unexpected keyword argument, `__tools__`.

**Root Cause:**
This is a straightforward error that occurs when an incorrect parameter name is used in the function call. The `fast_rlm.run` function does not have a parameter named `__tools__`.

**Solution:**
The fix is to replace the incorrect parameter with the correct one, `tools`. When making this change, ensure that you are also passing a list of callable functions, as detailed in the solution for the first error.

**Example:**
```python
# Incorrect: Using the wrong keyword argument
# response = await asyncio.to_thread(
#     fast_rlm.run,
#     query_prompt,
#     config=self.rlm_config,
#     __tools__=self._tool_functions,
#     verbose=True,
# )

# Correct: Using the 'tools' keyword and passing a list of functions
response = await asyncio.to_thread(
    fast_rlm.run,
    query_prompt,
    config=self.rlm_config,
    tools=list(self._tool_functions.values()),
    verbose=True,
)
```

---

### 3. Sub-Agent Errors (`TypeError: missing 'self'`, `NameError`, `ValueError: Tool source defined no callable`)

**Symptoms:**
When a sub-agent is created (e.g., by the `run_deep_rca_investigation` tool), you may encounter a cascade of errors:
- `TypeError: _run_deep_rca_investigation_tool() missing 1 required positional argument: 'self'`
- `NameError: name 'signal' is not defined`
- `ValueError: Tool source defined no callable`
- `NameError: name 'mcp_list_tools' is not defined`
- `NameError: name 'run_deep_rca_investigation' is not defined`

**Root Cause:**
All these errors stem from the same fundamental issue: **context leakage and recursion**. The `fast-rlm` sub-agent runs in a completely isolated environment and has no access to the main agent's `self` context, variables, or state. When we were passing the main agent's tools (including the one that *creates* the sub-agent) to the sub-agent itself, it caused numerous conflicts:
- The sub-agent couldn't execute methods that depended on `self`.
- It couldn't resolve `lambda` functions that were defined in the parent's context.
- It became confused by the parent's execution history and tried to call tools it didn't have, leading to `NameError`.

**Solution:**
The definitive solution is to treat the sub-agent as a pure, specialist tool. Its job is not to use the high-level tools of its parent, but to perform its task by writing and executing its own Python code.

This is achieved by giving the sub-agent a **clean environment with no tools at all**. This prevents all context-related errors and forces the sub-agent to rely on its intended capability.

**Example:**
In `base_agent.py`, the `_run_deep_rca_investigation_tool` was modified to call the sub-agent with an empty tool list.

```python
# In _run_deep_rca_investigation_tool:

# Incorrect: Passing the parent's tools, which causes context conflicts.
# sub_agent_tools = { ...omitted for brevity... }
# response = await asyncio.to_thread(
#     fast_rlm.run,
#     query_prompt,
#     config=self.rlm_config,
#     tools=list(sub_agent_tools.values()), # This caused the errors
#     verbose=True,
# )

# Correct: Give the sub-agent a clean environment with no tools.
try:
    # Run the sub-agent with NO tools.
    response = await asyncio.to_thread(
        fast_rlm.run,
        query_prompt,
        config=self.rlm_config,
        tools=[], # This is the fix
        verbose=True,
    )
```
This change acknowledges the different roles of the main agent and the sub-agent, creating a stable and predictable architecture.
