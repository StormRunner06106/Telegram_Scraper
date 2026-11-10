"""Real journal/CSV integration tests for deletion, reorder and retry recovery."""

from dataclasses import replace
import json

from githubscraper import core


def users(*names):
    return [{"username": name, "github_url": f"https://github.com/{name}"} for name in names]


def setup_run(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "REGION_STATE_DIR", tmp_path / "states")
    monkeypatch.setattr(core, "STATE_FILE", tmp_path / "legacy.json")
    output = tmp_path / "12_dallas_tx.csv"
    calls = []

    def validate(index, gate, user, *args):
        calls.append(user["username"])
        contact = core.Contact(user["github_url"], "", "@" + user["username"], "", 10, "", "matched")
        return core.ValidationOutcome(index, gate, user["username"], user["github_url"],
                                      contact, "Qualified lead", reason="qualified")

    monkeypatch.setattr(core, "validate_user_in_gate", validate)
    return output, calls, validate


def test_deleted_csv_is_rebuilt_even_after_completed_run(monkeypatch, tmp_path):
    output, calls, _ = setup_run(monkeypatch, tmp_path)
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: (users("a", "b"), False))
    assert core.scrape_region(12, output, delay_seconds=0) == 2
    assert core.get_region_state(12).is_end
    for shard in core.contact_shard_paths(output):
        shard.unlink()
    calls.clear()
    assert core.scrape_region(12, output, delay_seconds=0) == 2
    assert set(calls) == {"a", "b"}
    assert len(core.load_contact_family(output)) == 2


def test_reordered_results_and_new_profiles_do_not_skip_or_repeat_decisions(monkeypatch, tmp_path):
    output, calls, validate = setup_run(monkeypatch, tmp_path)

    def reject_b(index, gate, user, *args):
        result = validate(index, gate, user, *args)
        return replace(result, contact=None, reason="achievements") if user["username"] == "b" else result

    monkeypatch.setattr(core, "validate_user_in_gate", reject_b)
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: (users("a", "b"), False))
    core.scrape_region(12, output, delay_seconds=0)
    calls.clear()
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: (users("new", "b", "a"), False))
    assert core.scrape_region(12, output, delay_seconds=0) == 1
    assert calls == ["new"]
    assert len(core.load_contact_family(output)) == 2


def test_request_failures_are_retried_after_resume(monkeypatch, tmp_path):
    output, calls, validate = setup_run(monkeypatch, tmp_path)
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: (users("a"), False))

    def fail(index, gate, user, *args):
        result = validate(index, gate, user, *args)
        return replace(result, contact=None, error_message="HTTP request failed", reason="request_error")

    monkeypatch.setattr(core, "validate_user_in_gate", fail)
    core.scrape_region(12, output, delay_seconds=0)
    assert not core.get_region_state(12).is_end
    status_path = tmp_path / ".scraper-state/12_dallas_tx.status.json"
    status = json.loads(status_path.read_text())
    assert status["pending_profiles"] == 1
    assert status["validation_complete"] is False
    monkeypatch.setattr(core, "validate_user_in_gate", validate)
    assert core.scrape_region(12, output, delay_seconds=0) == 1
    assert calls == ["a", "a"]
    assert core.get_region_state(12).is_end
    assert json.loads(status_path.read_text())["pending_profiles"] == 0


def test_different_output_cannot_inherit_another_output_resume(monkeypatch, tmp_path):
    output, calls, _ = setup_run(monkeypatch, tmp_path)
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: (users("a"), False))
    core.scrape_region(12, output, delay_seconds=0)
    calls.clear()
    assert core.scrape_region(12, tmp_path / "other.csv", delay_seconds=0) == 1
    assert calls == ["a"]


def test_capped_runs_finish_saved_queue_before_rediscovering(monkeypatch, tmp_path):
    output, calls, _ = setup_run(monkeypatch, tmp_path)
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: (users("a", "b", "c"), False))
    assert core.scrape_region(12, output, max_results=1, delay_seconds=0) == 1
    calls.clear()
    def unexpected_search(*args, **kwargs):
        raise AssertionError("Pending validation queue should be reused")

    monkeypatch.setattr(core, "search_github_users", unexpected_search)
    assert core.scrape_region(12, output, max_results=1, delay_seconds=0) == 1
    assert calls == ["b"]


def test_no_resume_rechecks_rejected_profiles(monkeypatch, tmp_path):
    output, calls, validate = setup_run(monkeypatch, tmp_path)
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: (users("a"), False))

    def reject(index, gate, user, *args):
        return replace(validate(index, gate, user, *args), contact=None, reason="account_age")

    monkeypatch.setattr(core, "validate_user_in_gate", reject)
    core.scrape_region(12, output, delay_seconds=0)
    calls.clear()
    monkeypatch.setattr(core, "validate_user_in_gate", validate)
    assert core.scrape_region(12, output, delay_seconds=0, resume=False) == 1
    assert calls == ["a"]


def test_partial_output_deletion_recovers_only_missing_contacts(monkeypatch, tmp_path):
    output, calls, _ = setup_run(monkeypatch, tmp_path)
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: (users("a", "b"), False))
    core.scrape_region(12, output, delay_seconds=0)
    shard = core.contact_shard_paths(output)[0]
    fields, rows, has_bom = core.read_csv(shard)
    retained = [dict(row, is_read="true") for row in rows if row["telegramId"] == "@a"]
    core.write_csv(shard, fields, retained, has_bom)
    calls.clear()
    assert core.scrape_region(12, output, delay_seconds=0) == 1
    assert calls == ["b"]
    assert next(contact for contact in core.load_contacts(shard) if contact.telegramId == "@a").is_read


def test_resume_identity_survives_github_username_change(monkeypatch, tmp_path):
    output, calls, validate = setup_run(monkeypatch, tmp_path)
    old_user = {**users("old")[0], "id": "123"}
    new_user = {**users("new")[0], "id": "123"}
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: ([old_user], False))

    def reject(index, gate, user, *args):
        return replace(validate(index, gate, user, *args), contact=None, reason="achievements")

    monkeypatch.setattr(core, "validate_user_in_gate", reject)
    core.scrape_region(12, output, delay_seconds=0)
    calls.clear()
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: ([new_user], False))
    core.scrape_region(12, output, delay_seconds=0)
    assert calls == []
