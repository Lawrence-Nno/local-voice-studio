"""Resource cleanup without accessing destroyed Tkinter widgets."""
import logging
import threading


def start_cleanup(*actions):
    def clean():
        for action in actions:
            try:
                action()
            except Exception:
                logging.exception("Application shutdown cleanup failed")

    # Keep Python alive until resources are released, after the window disappears.
    worker = threading.Thread(target=clean, name="shutdown-cleanup", daemon=False)
    worker.start()
    return worker
