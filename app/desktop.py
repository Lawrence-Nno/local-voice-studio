"""Windowless entry point with local logging for packaged launches."""
import sys
from .storage import DATA


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "launch.log").open("a", encoding="utf-8", buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            if "--check" in sys.argv:
                from .portable_check import main as start
            else:
                from .main import main as start
            start()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__


if __name__ == "__main__":
    main()
