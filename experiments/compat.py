"""Compatibility names for code that imported the N1-Engine classes directly."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from experiments.analysis import bootstrap_ci, calculate_trend, correlation_matrix
from experiments.exporter import export_csv
from experiments.importer import import_csv
from experiments.reporting import generate_html_report


class AnalysisEngine:
    """Static subset of the source AnalysisEngine that does not need a DataFrame."""

    calculate_trend = staticmethod(calculate_trend)
    bootstrap_ci = staticmethod(bootstrap_ci)
    correlation_matrix = staticmethod(correlation_matrix)


class DataManager:
    """Bind the source CSV import/export methods to one host connection and program."""

    def __init__(self, conn: sqlite3.Connection, research_ref: str) -> None:
        self.conn = conn
        self.research_ref = research_ref

    def import_from_csv(self, filepath: Path | str, data_type: str = "metrics") -> dict:
        return import_csv(self.conn, self.research_ref, filepath, data_type)

    def export_to_csv(self, filepath: Path | str, data_type: str = "metrics") -> dict:
        return export_csv(self.conn, self.research_ref, filepath, data_type)


class ReportGenerator:
    """Source-compatible static report entry point."""

    generate_html_report = staticmethod(generate_html_report)
