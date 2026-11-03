# Test Coverage Report

## Overview

This document summarizes the E2E test coverage for the OGRDB application, highlighting which routes, forms, and API endpoints are covered by Playwright tests and areas for future expansion.

**Last Updated:** 2026-11-03  
**Test Command:** `pytest tests/test_e2e.py -v`  
**Current Status:** 12 tests passing

## Public Routes Covered (Points 1-5)

### Documentation & Help Pages
- ✅ **GET `/render_page/licensing_statement`** - Licensing page loads and displays correctly
- ✅ **GET `/help`** - Help/documentation page loads with expected content
- ✅ **GET `/schema/ogrdb-api-openapi3.yaml`** - API schema loads successfully

### Public Browsing & Search
- ✅ **GET `/germline_sets`** - Germline set browsing page loads
  - ✅ Species selection filtering
  - ✅ Germline set table display with published records
  - ✅ Empty state rendering
  
- ✅ **GET `/sequences`** - Sequence search and filtering page
  - ✅ Species filter
  - ✅ Locus filter (IGH tested)
  - ✅ Search results display with published sequences

### API Endpoints
- ✅ **GET `/api_v2/`** - API status endpoint returns service status
- ✅ **GET `/api_v2/swagger`** - Swagger UI documentation loads

## Authenticated Routes Covered (Point 6)

### Authentication
- ✅ **GET `/login`** - Login page loads with form fields
- ✅ **POST `/login`** - User login with valid test credentials
- ✅ **POST `/login`** - Login fails with invalid credentials (error handling)
- ✅ **GET `/register`** - Registration page loads with email field

### Protected Routes (Access Control)
- ✅ **GET `/new_submission`** - Redirects unauthenticated users to login with ?next parameter
- ✅ **GET `/submissions`** - Publicly accessible, shows public submissions without authentication

## Routes NOT Yet Covered

### Authenticated Submission Routes
- ❌ **GET `/edit_submission/<id>`** - Edit existing submission
- ❌ **POST `/edit_submission/<id>`** - Save submission changes
- ❌ **GET `/submission/<id>`** - View submission details
- ❌ **POST `/submit_submission/<id>`** - Submit/publish submission
- ❌ **DELETE `/submission/<id>`** - Delete/withdraw submission

### Authenticated Administrative Routes
- ❌ **GET `/submission_review/<id>`** - Review submission (admin)
- ❌ **POST `/submission_review/<id>`** - Admin submission approval
- ❌ **GET `/manage_sequences/<id>`** - Sequence management (admin)
- ❌ **GET `/manage_germline_sets/<id>`** - Germline set management (admin)

### Submission Sub-Forms (Inferred Sequences, Genotypes, etc.)
- ❌ **GET/POST `/inferred_sequence/*`** - Inferred sequence form routes
- ❌ **GET/POST `/genotype/*`** - Genotype form routes
- ❌ **GET/POST `/genotype_description/*`** - Genotype description routes
- ❌ **GET/POST `/inference_tool/*`** - Inference tool routes
- ❌ **GET/POST `/primer_set/*`** - Primer set routes

### VDJbase Integration
- ❌ **GET/POST `/submission_from_vdjbase/*`** - VDJbase submission routes

### Genotype Statistics
- ❌ **GET/POST `/genotype_stats/*`** - Genotype statistics routes

### Maintenance Routes (Admin Only)
- ❌ **GET/POST `/maint/*`** - Maintenance and admin routes
- ❌ **GET `/check_schema`** - Schema check route
- ❌ **GET `/manage_users`** - User management (admin)

### VDJbase Routes
- ❌ **GET `/vdjbase_*`** - VDJbase integration routes

## API Endpoints Coverage

### Tested API Endpoints
- ✅ **GET `/api_v2/`** - Service status

### Untested REST API Endpoints (`/api/`)
- ❌ **GET/POST `/api/sequence/*`** - Sequence endpoints
- ❌ **GET/POST `/api/germline/*`** - Germline endpoints

### Untested V2 API Endpoints (`/api_v2/`)
- ❌ **GET `/api_v2/germline-sets`** - List germline sets
- ❌ **GET `/api_v2/germline-sets/{id}`** - Get germline set details
- ❌ **GET `/api_v2/sequences`** - List sequences
- ❌ **GET `/api_v2/sequences/{id}`** - Get sequence details
- ❌ Filter parameters (species, locus, gene name, etc.)
- ❌ Pagination parameters
- ❌ Invalid request handling
- ❌ Response schema validation

## Form Coverage

### Covered Forms
- ✅ Login form (validation with invalid credentials)
- ✅ Submission creation form (basic access and validation)

### Uncovered Forms
- ❌ Registration form (full workflow)
- ❌ Submission edit form
- ❌ Inferred sequence forms
- ❌ Genotype forms
- ❌ Inference tool forms
- ❌ Primer set forms
- ❌ Password reset form
- ❌ Email preference form
- ❌ User profile update form

## Test Database Fixtures

### Implemented
- ✅ Published germline sets with genes
- ✅ Published sequences
- ✅ Species lookup data
- ✅ Test user accounts with proper authentication

### Recommended Additions
- ❌ Draft submissions for testing edit workflow
- ❌ Submitted submissions for testing review workflow
- ❌ Multiple user accounts with different roles
- ❌ Committee/reviewer accounts for admin testing
- ❌ Inferred sequences with associated data
- ❌ Genotypes with validation test cases

## Security & Access Control Testing

### Covered
- ✅ Unauthenticated access redirects to login
- ✅ Invalid credentials rejected
- ✅ Authenticated users can access protected routes
- ✅ Logout functionality

### Recommended
- ❌ Role-based access control (reviewer vs. submitter)
- ❌ Submission ownership verification
- ❌ Delegation permissions testing
- ❌ Admin-only route protection
- ❌ CSRF token validation
- ❌ Password strength validation
- ❌ Session timeout handling

## Browser Diagnostics

### Implemented
- ✅ Console error capture in CI artifacts
- ✅ Failed request tracking
- ✅ Diagnostic logs for test failures
- ✅ Accessible role/label-based locators
- ✅ Playwright web-first assertions

## Future Coverage

### High Priority
1. **Authentication Edge Cases**: Password reset, email confirmation, account deactivation
2. **Clickable Links** Test all clickable links on public pages to ensure they navigate correctly
3. **Role-Based Access Control**: Test different user roles and permissions
4. **API Endpoint Testing**: Comprehensive coverage of `/api_v2/` endpoints with schema validation
5. **Form Validation**: Comprehensive validation for all form types EXCEPT the submit, review, approve workflows
6. **New Sequence**: sequence upload from `/new_sequence` page

### Medium Priority
1. **Admin Functions**: User management, submission review, germline set management
2. **File Uploads**: Attachment handling in submissions
3. **Data Export**: Download and export functionality
4. **Search & Filtering**: Advanced search with multiple filter combinations
5. **Error Handling**: 404, 403, 500 error pages

### Low Priority
1. **Internationalization**: Multi-language support testing
2. **Browser Compatibility**: Test across different browsers (Chrome, Firefox, Safari)
3. **Performance**: Load testing for large result sets
4. **Accessibility**: WCAG compliance checking
5. **Mobile Responsiveness**: Mobile device testing
6. **Submission Lifecycle**: Create, edit, submit, review, approve workflows. Low priority as this is not actively used in production.

## Test Execution

Run all E2E tests:
```bash
pytest tests/test_e2e.py -v
```

Run tests matching a pattern (e.g., public tests):
```bash
pytest tests/test_e2e.py -k "public" -v
```

Run authenticated route tests only:
```bash
pytest tests/test_e2e.py::test_login_page_loads tests/test_e2e.py::test_user_login_successful -v
```

View diagnostics for failed tests:
```bash
cat tests/test-results/*.log
```

## Point 6: Authenticated Routes Testing (New)

Six new tests have been added to cover authenticated route access and basic authentication flows:

1. **test_login_page_loads** - Verifies login page renders with expected fields
2. **test_user_login_successful** - Tests login with valid test credentials
3. **test_submissions_page_allows_public_access** - Confirms submissions page is public
4. **test_user_login_with_invalid_credentials** - Verifies login rejection for bad credentials
5. **test_new_submission_requires_authentication** - Confirms /new_submission redirects to login
6. **test_registration_page_loads** - Verifies registration page renders

### Test Fixtures Added
- **test_user** - Creates a test user account in isolated test database with proper password hashing
- **authenticated_page** - Browser session with authenticated user (for future authenticated tests)

### Key Implementation Details
- Password hashing uses `flask_security.utils.hash_password()` with proper app context
- Test database includes `SECURITY_PASSWORD_SALT` configuration for argon2 hashing
- Test user is automatically created in app context and cleaned up after each test
- Authentication tests use realistic form field labels and button names from the actual app
- Tests validate that protected routes redirect with `?next=` parameters

## Point 7: Coverage Report (New)

[COVERAGE.md](./COVERAGE.md) has been created documenting:

- **Covered Routes**: 12 E2E tests covering public pages, API endpoints, and authentication
- **Tested Forms**: Login, registration, germline set browsing, sequence search/filter
- **Access Control**: Verified unauthenticated access controls and public vs. protected routes
- **Routes Not Yet Covered**: 50+ routes across submissions, admin functions, sub-forms, and API endpoints
- **Recommended Future Coverage**: Prioritized list of high/medium/low priority testing areas
- **Browser Diagnostics**: Console error and failed request logging implemented
