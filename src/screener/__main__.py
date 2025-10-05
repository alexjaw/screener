#!/usr/bin/env python3
"""Main CLI entry point for the screener package."""

import sys
from .cli.screener_cli import main as screener_main
from .cli.fscore_cli import main as fscore_main
from .cli.ticker_cli import main as ticker_main

def main():
    """Main entry point that routes to appropriate CLI based on command."""
    if len(sys.argv) < 2:
        print("Usage: screener <command> [options]")
        print("Commands:")
        print("  screener    - Run momentum screening")
        print("  fscore      - Calculate F-Scores")
        print("  ticker      - Get ticker data")
        sys.exit(1)
    
    command = sys.argv[1]
    sys.argv = sys.argv[1:]  # Remove the command from argv
    
    if command == "screener":
        screener_main()
    elif command == "fscore":
        fscore_main()
    elif command == "ticker":
        ticker_main()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: screener, fscore, ticker")
        sys.exit(1)

if __name__ == "__main__":
    main()
