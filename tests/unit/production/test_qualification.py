from __future__ import annotations

import json

from l1_microstructure.production.qualification import (
    QUALIFICATION_FAILURE_EXIT_CODE,
    QUALIFICATION_SUCCESS_EXIT_CODE,
    ProductionQualification,
    ProductionQualificationReport,
    QualificationCheck,
    QualificationScenarioResult,
    main,
)


def test_production_qualification_passes_all_offline_safety_drills() -> None:
    report = ProductionQualification().run()

    assert report.passed is True
    assert [scenario.name for scenario in report.scenarios] == list(ProductionQualification.SCENARIO_NAMES)
    assert all(scenario.passed for scenario in report.scenarios)
    assert report.to_dict()["schema_version"] == 1
    assert report.to_dict()["status"] == "passed"


def test_production_qualification_can_select_one_scenario() -> None:
    report = ProductionQualification().run(("stale_feed_halt", "stale_feed_halt"))

    assert report.passed is True
    assert [scenario.name for scenario in report.scenarios] == ["stale_feed_halt"]


def test_production_qualification_isolates_scenario_exceptions() -> None:
    def fail(_root):
        raise RuntimeError("sensitive diagnostic")

    report = ProductionQualification({"failing_drill": fail}).run(("failing_drill",))

    assert report.passed is False
    payload = report.to_dict()
    assert payload["scenarios"][0]["checks"][0]["details"] == {"error_type": "RuntimeError"}
    assert "sensitive diagnostic" not in json.dumps(payload)


def test_qualification_cli_emits_json_and_stable_success_code(capsys) -> None:
    exit_code = main(["--scenario", "broker_disconnect_halt"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == QUALIFICATION_SUCCESS_EXIT_CODE
    assert payload["status"] == "passed"
    assert payload["scenario_count"] == 1
    assert payload["scenarios"][0]["name"] == "broker_disconnect_halt"


def test_qualification_cli_emits_redacted_failure_and_stable_code(monkeypatch, capsys) -> None:
    def fail(_self, _selected=None):
        raise RuntimeError("sensitive runtime detail")

    monkeypatch.setattr(ProductionQualification, "run", fail)

    exit_code = main([])

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == QUALIFICATION_FAILURE_EXIT_CODE
    assert payload["status"] == "failed"
    assert payload["scenarios"][0]["checks"][0]["details"] == {"error_type": "RuntimeError"}
    assert "sensitive runtime detail" not in output


def test_empty_qualification_report_fails_closed() -> None:
    report = ProductionQualificationReport(())
    failed_scenario = QualificationScenarioResult(
        "failed",
        (QualificationCheck("failed.check", False, "failed"),),
    )

    assert report.passed is False
    assert failed_scenario.passed is False
