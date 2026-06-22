import io
from temporalio import activity

class HeartbeatingStream(io.StringIO):
    """
    An in-memory stream that sends its contents as Temporal heartbeats.
    This is useful for capturing logs from a long-running process and
    making them visible in the Temporal UI.
    """
    def write(self, s):
        if s and s.strip():
            # Temporal has a size limit on heartbeat details, so we truncate.
            details = s[:2000]
            try:
                activity.heartbeat(details)
                # Also log to the worker's console for local debugging.
                print(details)
            except RuntimeError:
                # This will be thrown if not in an activity context, which is fine.
                pass
        super().write(s)
