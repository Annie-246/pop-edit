#!/usr/bin/env python3
"""Điểm vào: python popedit.py <lệnh> ...   (xem -h)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from popedit.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
