#!/usr/bin/env python3
"""Thin alias — frontier_worker.py maps to frontier_agent.py (P2 gap closure)."""

from frontier_agent import FrontierAgent, main

__all__ = ["FrontierAgent", "main"]

if __name__ == "__main__":
    main()
