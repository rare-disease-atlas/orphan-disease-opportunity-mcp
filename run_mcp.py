#!/usr/bin/env python3
"""Standalone MCPB / CLI entrypoint for orphan-disease-opportunity-mcp."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orphan_disease_mcp.server import main

if __name__ == "__main__":
    main()
