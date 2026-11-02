from playwright.sync_api import expect


def test_public_licensing_page_loads(page, live_server, browser_diagnostics):
    page.goto(f"{live_server}/render_page/licensing_statement")

    expect(page.get_by_role("heading", name="Source Code")).to_be_visible()
    expect(page.get_by_role("link", name="GitHub")).to_be_visible()


def test_public_api_status_loads(page, live_server, browser_diagnostics):
    page.goto(f"{live_server}/api_v2/")

    expect(page.get_by_text("Service is up.")).to_be_visible()


def test_public_germline_set_browsing(
    page, live_server, published_records, browser_diagnostics
):
    page.goto(f"{live_server}/germline_sets")

    page.get_by_label("Species").select_option(label=published_records["species"])
    page.get_by_role("button", name="Show Germline Sets").click()

    expect(page.get_by_role("heading", name="Published Sets", exact=False)).to_be_visible()
    expect(page.get_by_role("link", name=published_records["germline_set_name"])).to_be_visible()


def test_public_sequence_search_and_filter(
    page, live_server, published_records, browser_diagnostics
):
    page.goto(f"{live_server}/sequences")

    page.get_by_label("Species").select_option(label=published_records["species"])
    page.get_by_label("Locus").select_option(label="IGH")
    page.get_by_role("button", name="Show Sequences").click()

    expect(page.get_by_role("heading", name="Affirmed Sequences", exact=True)).to_be_visible()
    expect(page.get_by_text(published_records["gene_name"], exact=False)).to_be_visible()


def test_public_documentation_and_api_schema_load(page, live_server, browser_diagnostics):
    page.goto(f"{live_server}/help")
    expect(page.get_by_role("heading", name="Data Access Quick Start")).to_be_visible()
    expect(page.get_by_role("link", name="Browse Sets")).to_be_visible()

    response = page.request.get(f"{live_server}/schema/ogrdb-api-openapi3.yaml")
    assert response.status == 200
    assert "openapi:" in response.text()


def test_public_germline_set_page_renders_empty_state(
    page, live_server, browser_diagnostics
):
    page.goto(f"{live_server}/germline_sets")

    expect(page.get_by_role("heading", name="Germline Sets")).to_be_visible()
    expect(page.get_by_label("Species")).to_be_visible()
