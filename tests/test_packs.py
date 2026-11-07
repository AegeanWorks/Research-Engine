"""Domain-pack registry: an isolated pack is declared, not imported across domains."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engine.artifacts import digest_tree
from engine.errors import EngineError
from engine.packs import (
    PACK_API_VERSION,
    get_pack,
    list_packs,
    register_pack,
    register_pack_from_tree,
)
from tests.support import DatabaseCase


class PackRegistryTests(DatabaseCase):
    def test_register_and_read_a_pack(self) -> None:
        pack = register_pack(
            self.conn,
            "fluid_universe",
            "0.2.0",
            data_root="../../fluid-universe/results",
            manifest_sha256="a" * 64,
        )
        self.assertEqual(pack.api_version, PACK_API_VERSION)
        self.assertEqual(get_pack(self.conn, "fluid_universe").version, "0.2.0")
        self.assertEqual([row.name for row in list_packs(self.conn)], ["fluid_universe"])

    def test_duplicate_pack_is_refused(self) -> None:
        register_pack(self.conn, "pnn", "1.0.0")
        self.assertRaises(EngineError, register_pack, self.conn, "pnn", "1.1.0")

    def test_invalid_api_version_is_refused(self) -> None:
        self.assertRaises(
            EngineError,
            register_pack,
            self.conn,
            "atlas",
            "1.0.0",
            api_version="something/else",
        )

    def test_invalid_manifest_digest_is_refused(self) -> None:
        self.assertRaises(
            EngineError,
            register_pack,
            self.conn,
            "obezite",
            "1.0.0",
            manifest_sha256="not-a-digest",
        )

    def test_pack_data_root_is_a_reference_not_a_copy(self) -> None:
        pack = register_pack(self.conn, "pnn", "1.0.0", data_root="D:/external/pnn/output")
        self.assertEqual(pack.data_root, "D:/external/pnn/output")
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) AS n FROM domain_pack").fetchone()["n"], 1
        )

    def test_register_pack_from_tree_fingerprints_external_data(self) -> None:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(directory, ignore_errors=True))
        (directory / "results").mkdir()
        (directory / "results" / "run.json").write_text('{"ok": true}\n', encoding="utf-8")
        (directory / "results" / "report.md").write_text("# report\n", encoding="utf-8")
        summary = digest_tree(directory, suffixes=(".json", ".md"))
        self.assertEqual(summary["files"], 2)
        pack = register_pack_from_tree(self.conn, "fluid_universe", "0.2.0", directory)
        self.assertEqual(pack.manifest_sha256, summary["sha256"])
        self.assertEqual(pack.data_root, str(directory))
        (directory / "results" / "run.json").write_text('{"ok": false}\n', encoding="utf-8")
        changed = digest_tree(directory, suffixes=(".json", ".md"))
        self.assertNotEqual(changed["sha256"], summary["sha256"])

    def test_register_pack_from_empty_tree_is_refused(self) -> None:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(directory, ignore_errors=True))
        with self.assertRaises(EngineError):
            register_pack_from_tree(self.conn, "atlas", "1.0.0", directory)
