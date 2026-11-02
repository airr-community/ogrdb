# E2E testing plan

The current Playwright tests are smoke tests for public content and the v2 API
health endpoint. Expand coverage in small steps:

1. Inventory route decorators, methods, and authorization checks. Keep the E2E
   scope to routes and forms that do not require a password or authenticated
   session; do not test login, registration, account recovery, or protected
   submissions.
2. Add browser journeys for public germline-set and sequence browsing, search
   and filtering, and public help/documentation pages. Exercise forms only
   where their route is publicly accessible and does not request a password.
   For pages showing the current versions of reference data, test overall page
   correctness—such as successful rendering, expected controls and headings,
   and functioning search or filtering—without asserting data-dependent counts
   or the presence of particular sequences or genes. These data can change over
   time.
3. Add deterministic database fixtures for published germline sets, sequences,
   species, and lookup data. Verify rendered results, empty states, downloads,
   and validation feedback, and remove fixture data after each test. Content
   assertions are appropriate for these controlled fixtures and for retrieval
   of explicitly specified, versioned reference sets; do not make equivalent
   assertions against dynamic current-version pages.
4. Audit the endpoints in `api/` and `api_v2/`. Cover successful responses,
   response schemas, pagination/filter parameters, and invalid requests using
   Flask's test client where browser interaction adds no value. Keep a small
   number of browser checks for the public API documentation and health paths.
5. Capture browser console errors and failed requests in CI artifacts when a
   browser test fails, and use accessible role- and label-based locators with
   Playwright web-first assertions throughout.
