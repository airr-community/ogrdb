import re

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

    expect(page.get_by_role("heading", name=re.compile(r"^\W*Affirmed Sequences$"))).to_be_visible()
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


# Tests for authenticated routes (Point 6)

def test_login_page_loads(page, live_server, browser_diagnostics):
    """Test that the login page loads and displays the sign-in form."""
    page.goto(f"{live_server}/login")

    expect(page.get_by_role("heading", name="Login")).to_be_visible()
    expect(page.get_by_label("Email Address")).to_be_visible()
    expect(page.get_by_label("Password")).to_be_visible()
    expect(page.get_by_role("button", name="Login")).to_be_visible()


def test_user_login_successful(page, live_server, test_user, browser_diagnostics):
    """Test successful user login and redirect to submissions page."""
    page.goto(f"{live_server}/login")

    page.get_by_label("Email Address").fill(test_user["email"])
    page.get_by_role("textbox", name="Password").fill(test_user["password"])
    page.get_by_role("button", name="Login").click()

    # Wait for page load after login attempt
    page.wait_for_load_state("networkidle", timeout=10000)
    
    # Check if login was successful (redirected from login page)
    url = page.url
    # Should either be on submissions or stay on login if there was an error
    assert "/login" not in url or "/submissions" in url, f"Login failed, still on login page: {url}"


def test_submissions_page_allows_public_access(page, live_server, browser_diagnostics):
    """Test that /submissions page is publicly accessible and shows public submissions."""
    page.goto(f"{live_server}/submissions")

    # Should show the page with public submissions section
    expect(page.get_by_role("heading", name="Submissions", exact=False)).to_be_visible()
    expect(page.get_by_text("Published Submissions", exact=False)).to_be_visible()


def test_user_login_with_invalid_credentials(page, live_server, browser_diagnostics):
    """Test login fails with invalid credentials."""
    page.goto(f"{live_server}/login")

    page.get_by_label("Email Address").fill("invalid@example.com")
    page.get_by_role("textbox", name="Password").fill("wrongpassword")
    page.get_by_role("button", name="Login").click()

    # Should stay on login page or show error
    page.wait_for_load_state("networkidle", timeout=10000)
    url = page.url
    assert "/login" in url, f"Expected login in URL after failed auth, got {url}"


def test_new_submission_requires_authentication(page, live_server, browser_diagnostics):
    """Test that accessing new submission page without authentication redirects to login."""
    page.goto(f"{live_server}/new_submission")

    # Should redirect to login page. Check URL starts with login
    url = page.url
    assert "/login" in url, f"Expected login in URL, got {url}"


def test_registration_page_loads(page, live_server, browser_diagnostics):
    """Test that the registration page loads."""
    page.goto(f"{live_server}/register")

    expect(page.get_by_role("heading", name="Register", exact=False)).to_be_visible()
    expect(page.get_by_label("Email Address")).to_be_visible()


def test_profile_requires_authentication(page, live_server, browser_diagnostics):
    page.goto(f"{live_server}/profile")

    expect(page).to_have_url(re.compile(r".*/login(?:\?.*)?$"))


def test_authenticated_user_can_update_profile(
    authenticated_page, browser_diagnostics
):
    name_field = authenticated_page.get_by_label("Full Name")
    address_field = authenticated_page.get_by_label("Institution and Postal Address")

    expect(name_field).to_have_value("Test User")
    expect(address_field).to_have_value("Test Address")
    name_field.fill("")
    expect(name_field).to_have_attribute("required", "")
    expect(
        name_field.evaluate("(field) => field.validity.valueMissing")
    ).to_be(True)

    name_field.fill("Updated Test User")
    address_field.fill("Updated Test Address")
    authenticated_page.get_by_role("button", name="Save Changes").click()

    expect(authenticated_page.get_by_text("Profile updated.")).to_be_visible()
    expect(name_field).to_have_value("Updated Test User")
    expect(address_field).to_have_value("Updated Test Address")


def test_authenticated_user_can_access_new_submission_form(
    authenticated_page, live_server, browser_diagnostics
):
    authenticated_page.goto(f"{live_server}/new_submission")

    expect(authenticated_page.get_by_text("Test User", exact=True)).to_be_visible()
    expect(authenticated_page.get_by_text("Test Address", exact=True)).to_be_visible()
    expect(authenticated_page.get_by_role("button", name="Create")).to_be_visible()
