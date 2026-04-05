"""Backward-compatible wrapper for running session summary from old script path."""

from focussight.summary import *  # noqa: F401,F403
from focussight.summary import main


if __name__ == "__main__":
    main()
