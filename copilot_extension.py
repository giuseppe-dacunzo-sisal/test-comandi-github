#!/usr/bin/env python3
"""
GitHub Copilot Extension - Entry Point
Supporta modalità locale e GitHub App pubblica
"""

import sys
import os

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import main

if __name__ == "__main__":
    sys.exit(main())
