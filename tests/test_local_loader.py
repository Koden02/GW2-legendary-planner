from pathlib import Path
from shutil import copytree

import pytest

from gw2_legendary_planner.api.local import LocalExportError, LocalExportLoader

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"


def test_local_loader_loads_supported_exports() -> None:
    snapshot = LocalExportLoader(FIXTURE_DIR).load()

    assert snapshot.account.name == "Example.1234"
    assert len(snapshot.wallet) == 5
    assert snapshot.wallet_value(63) == 1200
    assert len(snapshot.achievements) == 2
    assert snapshot.achievement_current(910) == 3
    assert snapshot.achievement_done(1)
    assert len(snapshot.materials) == 2
    assert len(snapshot.bank) == 3
    assert len(snapshot.shared_inventory) == 2
    assert len(snapshot.legendary_armory) == 2
    assert snapshot.characters[0].name == "Ariadne Example"


def test_local_loader_reports_missing_required_exports(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "account.json").write_text('{"name": "Partial.1234"}', encoding="utf-8")

    with pytest.raises(LocalExportError) as exc_info:
        LocalExportLoader(export_dir).load()

    codes = {issue.code for issue in exc_info.value.report.issues}
    assert "missing_endpoint_export" in codes
    assert "Missing wallet export." in str(exc_info.value)


def test_local_loader_reports_malformed_json(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    copytree(FIXTURE_DIR, export_dir)
    (export_dir / "account_wallet.json").write_text("[", encoding="utf-8")

    report = LocalExportLoader(export_dir).validate()

    assert not report.is_valid
    assert report.issues[0].code == "malformed_json"
    assert "Malformed JSON" in report.issues[0].message


def test_local_loader_reports_wrong_payload_shape(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    copytree(FIXTURE_DIR, export_dir)
    (export_dir / "account_wallet.json").write_text("{}", encoding="utf-8")

    report = LocalExportLoader(export_dir).validate()

    assert not report.is_valid
    assert report.issues[0].code == "invalid_payload_shape"
    assert "expected JSON array" in report.issues[0].message


def test_local_loader_reports_unsupported_endpoint_versions(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    copytree(FIXTURE_DIR, export_dir)
    (export_dir / "v1_account.json").write_text("{}", encoding="utf-8")

    report = LocalExportLoader(export_dir).validate()

    assert not report.is_valid
    assert report.issues[0].code == "unsupported_endpoint_version"
