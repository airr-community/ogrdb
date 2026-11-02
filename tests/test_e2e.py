from playwright.sync_api import expect


def test_public_licensing_page_loads(page, live_server):
    page.goto(f"{live_server}/render_page/licensing_statement")

    expect(page.get_by_role("heading", name="Source Code")).to_be_visible()
    expect(page.get_by_role("link", name="GitHub")).to_be_visible()


def test_public_api_status_loads(page, live_server):
    page.goto(f"{live_server}/api_v2/")

    expect(page.get_by_text("Service is up.")).to_be_visible()
