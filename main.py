#!/usr/bin/env python3
"""
MagicSplitGPT 메인 실행 파일
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.main import main

if __name__ == "__main__":
    main()