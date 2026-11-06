"""Optional real-browser tests: GSCRAPER_BROWSER_TESTS=1 python -m pytest -q.

Requires Playwright and Chromium (or Edge on Windows). No external sites are
contacted, and every CSV used by these checks lives in pytest's temp directory.
"""

import os
from threading import Thread

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("GSCRAPER_BROWSER_TESTS") != "1", reason="opt-in browser checks")
playwright_api = pytest.importorskip("playwright.sync_api")
expect = playwright_api.expect

from githubscraper.csv_storage import read_csv, write_csv
from githubscraper.ui import create_server


@pytest.fixture(scope="module")
def browser():
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge" if os.name == "nt" else None, headless=True)
        yield browser
        browser.close()


@pytest.fixture
def workspace(tmp_path, browser):
    first = {"link": "https://example.com/first", "email": "first@example.com", "telegramId": "@first", "company": "A very long company name that stays on one line", "notes": 'Hello, "world"\n日本語', "custom": '<img src=x onerror="alert(1)">'}
    second = {**first, "link": "https://example.com/second", "email": "second@example.com"}
    write_csv(tmp_path / "a_contacts.csv", list(first), [first, second])
    write_csv(tmp_path / "regions" / "b_contacts.csv", ["link", "company"], [{"link": "https://example.com/third", "company": "Third company"}])
    server = create_server(tmp_path, 0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    context = browser.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    context.route("https://**/*", lambda route: route.abort())
    page = context.new_page()
    page.set_default_timeout(8000)
    errors = []
    page.on("pageerror", lambda failure: errors.append(str(failure)))
    page.goto(url)
    expect(page.locator("tbody tr")).to_have_count(2)
    yield page, tmp_path, first
    context.close()
    server.shutdown()
    server.server_close()
    thread.join()
    assert errors == []


def test_copy_links_manual_read_and_file_menu(workspace):
    page, root, first = workspace
    cells = page.locator("tbody tr").first.locator("td")
    expect(page.locator("tbody img")).to_have_count(0)
    cells.nth(4).click()
    assert page.evaluate("navigator.clipboard.readText()") == first["company"]
    checkbox = cells.first.locator("input")
    expect(checkbox).to_be_checked()
    expect(checkbox).to_be_enabled()
    assert read_csv(root / "a_contacts.csv")[1][0]["is_read"] == "true"
    expect(page.locator("tbody tr").nth(1).locator("input")).not_to_be_checked()
    cells.nth(5).click()
    assert page.evaluate("navigator.clipboard.readText()").replace("\r\n", "\n") == first["notes"]
    checkbox = cells.first.locator("input")
    checkbox.check()
    expect(checkbox).to_be_enabled()
    expect(checkbox).to_be_checked()
    assert read_csv(root / "a_contacts.csv")[1][0]["is_read"] == "true"
    checkbox.uncheck()
    expect(checkbox).to_be_enabled()
    expect(checkbox).not_to_be_checked()
    assert read_csv(root / "a_contacts.csv")[1][0]["is_read"] == "false"
    with page.expect_popup() as opened:
        cells.nth(1).locator("a").click()
    opened.value.close()
    expect(checkbox).to_be_checked()
    expect(checkbox).to_be_enabled()
    assert read_csv(root / "a_contacts.csv")[1][0]["is_read"] == "true"
    page.reload()
    expect(page.locator("tbody tr").first.locator("input")).to_be_checked()
    page.get_by_role("button", name="b_contacts.csv").click()
    expect(page.locator("tbody tr")).to_have_count(1)
    expect(page.locator("h1")).to_have_text("b_contacts.csv")
    page.get_by_role("button", name="a_contacts.csv").click()
    expect(page.locator("tbody tr")).to_have_count(2)
    expect(page.locator("tbody tr").first.locator("input")).to_be_checked()


def test_widths_sidebar_and_copy_preferences_persist(workspace):
    page, _, first = workspace
    page.get_by_role("button", name="Settings", exact=True).click()
    page.get_by_label("Copy on click", exact=True).uncheck()
    width = page.get_by_label("company column width", exact=True)
    width.fill("310")
    width.press("Tab")
    page.get_by_label("Show CSV sidebar", exact=True).uncheck()
    page.get_by_role("button", name="Done", exact=True).click()
    expect(page.locator("#sidebar")).to_be_hidden()
    cell = page.locator("tbody tr").first.locator("td").nth(4)
    assert abs(cell.bounding_box()["width"] - 310) < 2
    page.evaluate("navigator.clipboard.writeText('unchanged')")
    cell.click()
    assert page.evaluate("navigator.clipboard.readText()") == "unchanged"
    expect(page.locator("tbody tr").first.locator("input")).not_to_be_checked()
    page.reload()
    expect(page.locator("tbody tr")).to_have_count(2)
    expect(page.locator("#sidebar")).to_be_hidden()
    assert abs(cell.bounding_box()["width"] - 310) < 2
    assert cell.evaluate("e => getComputedStyle(e).whiteSpace") == "nowrap"
    handle = page.get_by_role("separator", name="Resize company", exact=True)
    handle.scroll_into_view_if_needed()
    box = handle.bounding_box()
    page.mouse.move(box["x"] + 4, box["y"] + 20)
    page.mouse.down()
    page.mouse.move(box["x"] + 84, box["y"] + 20, steps=5)
    page.mouse.up()
    assert abs(cell.bounding_box()["width"] - 390) < 2
    page.reload()
    expect(page.locator("tbody tr")).to_have_count(2)
    assert abs(cell.bounding_box()["width"] - 390) < 2
    page.get_by_role("button", name="Toggle CSV sidebar").click()
    expect(page.locator("#sidebar")).to_be_visible()
    page.get_by_role("button", name="Settings", exact=True).click()
    expect(page.get_by_label("Copy on click", exact=True)).not_to_be_checked()
    page.get_by_role("button", name="Restore defaults").click()
    expect(page.get_by_label("Copy on click", exact=True)).to_be_checked()
    page.get_by_role("button", name="Done", exact=True).click()
    cell.click()
    assert page.evaluate("navigator.clipboard.readText()") == first["company"]


def test_drag_copy_does_not_open_link_and_middle_click_marks_read(workspace):
    page, root, _ = workspace
    page.get_by_role("button", name="Settings", exact=True).click()
    page.get_by_label("Copy a drag selection", exact=True).check()
    page.get_by_role("button", name="Done", exact=True).click()
    anchor = page.locator("tbody tr").first.locator("a").first
    box = anchor.bounding_box()
    page.mouse.move(box["x"] + 3, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] - 5, box["y"] + box["height"] / 2, steps=16)
    page.mouse.up()
    selection = page.evaluate("getSelection().toString()")
    assert len(selection) > 5
    assert page.evaluate("navigator.clipboard.readText()") == selection
    assert len(page.context.pages) == 1
    checkbox = page.locator("tbody tr").first.locator("input")
    expect(checkbox).to_be_checked()
    expect(checkbox).to_be_enabled()
    assert read_csv(root / "a_contacts.csv")[1][0]["is_read"] == "true"
    page.evaluate("getSelection().removeAllRanges()")
    checkbox.uncheck()
    expect(checkbox).to_be_enabled()
    with page.context.expect_page() as opened:
        anchor.click(button="middle")
    opened.value.close()
    expect(page.locator("tbody tr").first.locator("input")).to_be_checked()
    assert read_csv(root / "a_contacts.csv")[1][0]["is_read"] == "true"


def test_failed_save_restores_checkbox_and_reports_error(workspace):
    page, root, _ = workspace
    before = (root / "a_contacts.csv").read_bytes()
    page.route("**/api/read", lambda route: route.fulfill(status=423, content_type="application/json", body='{"error":"CSV is locked. Try again."}'))
    checkbox = page.locator("tbody tr").first.locator("input")
    checkbox.click()
    expect(page.get_by_role("alert")).to_contain_text("Could not save a_contacts.csv: CSV is locked")
    expect(checkbox).to_be_enabled()
    expect(checkbox).not_to_be_checked()
    assert (root / "a_contacts.csv").read_bytes() == before


def test_native_copy_marks_only_the_selected_row(workspace):
    page, root, first = workspace
    cell = page.locator("tbody tr").nth(1).locator("td").nth(4)
    cell.focus()
    cell.evaluate("""element => {
        const range = document.createRange();
        range.selectNodeContents(element);
        getSelection().removeAllRanges();
        getSelection().addRange(range);
    }""")
    checkbox = page.locator("tbody tr").nth(1).locator("input")
    expect(checkbox).not_to_be_checked()
    assert read_csv(root / "a_contacts.csv")[1][1]["is_read"] == "false"
    page.keyboard.press("ControlOrMeta+c")
    assert page.evaluate("navigator.clipboard.readText()") == first["company"]
    expect(checkbox).to_be_checked()
    expect(checkbox).to_be_enabled()
    assert [row["is_read"] for row in read_csv(root / "a_contacts.csv")[1]] == ["false", "true"]
    page.reload()
    expect(page.locator("tbody tr").nth(1).locator("input")).to_be_checked()


@pytest.mark.parametrize("mode", ["clipboard", "fallback"])
def test_failed_copy_does_not_mark_read(workspace, mode):
    page, root, _ = workspace
    if mode == "clipboard":
        page.evaluate("() => { navigator.clipboard.writeText = async () => { throw new Error('denied'); }; }")
    else:
        page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: undefined}); document.execCommand = () => false;")
    requests = []
    page.on("request", lambda request: requests.append(request.url) if request.url.endswith("/api/read") else None)
    page.locator("tbody tr").first.locator("td").nth(4).click()
    expect(page.get_by_role("alert")).to_contain_text("Could not copy")
    expect(page.locator("tbody tr").first.locator("input")).not_to_be_checked()
    assert requests == []
    assert read_csv(root / "a_contacts.csv")[1][0]["is_read"] == "false"


def test_copy_finishing_after_file_switch_marks_original_file(workspace):
    page, root, _ = workspace
    page.evaluate("() => { navigator.clipboard.writeText = () => new Promise(resolve => { window.finishCopy = resolve; }); }")
    page.locator("tbody tr").first.locator("td").nth(4).click()
    page.get_by_role("button", name="b_contacts.csv").click()
    expect(page.locator("tbody tr")).to_have_count(1)
    with page.expect_response("**/api/read") as saved:
        page.evaluate("window.finishCopy()")
    assert saved.value.status == 200
    assert read_csv(root / "a_contacts.csv")[1][0]["is_read"] == "true"
    assert read_csv(root / "regions" / "b_contacts.csv")[1][0]["is_read"] == "false"
    expect(page.locator("tbody tr").first.locator("input")).not_to_be_checked()


def test_copy_during_unread_save_is_not_lost(workspace):
    page, root, _ = workspace
    checkbox = page.locator("tbody tr").first.locator("input")
    checkbox.check()
    expect(checkbox).to_be_enabled()
    pending = []
    page.route("**/api/read", lambda route: pending.append(route) if not route.request.post_data_json["is_read"] else route.continue_())
    with page.expect_request("**/api/read"):
        checkbox.uncheck()
    expect(checkbox).to_be_disabled()
    page.locator("tbody tr").first.locator("td").nth(4).click()
    expect(page.locator("#toast")).to_have_text("Copied to clipboard")
    pending[0].continue_()
    expect(checkbox).to_be_checked()
    expect(checkbox).to_be_enabled()
    assert read_csv(root / "a_contacts.csv")[1][0]["is_read"] == "true"
