"""
dirty-waters - A tool to detect software supply chain smells and issues
"""

from .main import main
from .report_static import write_summary
from .report_diff import generate_diff_report

__version__ = "0.1.1"
__author__ = "CHAINS research project at KTH Royal Institute of Technology"

__all__ = ["main", "write_summary", "generate_diff_report"]
