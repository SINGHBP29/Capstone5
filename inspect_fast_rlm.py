import fast_rlm
import inspect

with open("fast_rlm_inspection.txt", "w") as f:
    f.write("--- fast_rlm.run signature ---\n")
    try:
        f.write(str(inspect.signature(fast_rlm.run)) + "\n\n")
    except Exception as e:
        f.write(f"Error getting signature: {e}\n\n")

    f.write("--- fast_rlm.RLMConfig signature ---\n")
    try:
        f.write(str(inspect.signature(fast_rlm.RLMConfig)) + "\n\n")
    except Exception as e:
        f.write(f"Error getting signature: {e}\n\n")

    f.write("--- fast_rlm.run docstring ---\n")
    try:
        f.write(str(inspect.getdoc(fast_rlm.run)) + "\n\n")
    except Exception as e:
        f.write(f"Error getting docstring: {e}\n\n")

    f.write("--- fast_rlm.RLMConfig docstring ---\n")
    try:
        f.write(str(inspect.getdoc(fast_rlm.RLMConfig)) + "\n\n")
    except Exception as e:
        f.write(f"Error getting docstring: {e}\n\n")
