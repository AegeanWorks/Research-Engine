"""Domain-pack registry: an isolated pack is declared, not imported across domains."""

from __future__ import annotations

import unittest

from engine.errors import EngineError
from engine.packs import PACK_API_VERSION, get_pack, list_packs, register_pack
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
