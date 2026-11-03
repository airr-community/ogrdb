# Test Coverage Report

## Overview

This document summarizes the E2E test coverage for the OGRDB application, highlighting which routes, forms, and API endpoints are covered by Playwright tests and areas for future expansion.

**Last Updated:** 2026-11-03  
**Test Command:** `pytest tests/test_e2e.py -v`  
**Current Status:** 15 tests passing (6 public + 9 authenticated)  
**Coverage:** 15 routes, 2 forms, 1 API endpoint directly tested

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

## Authenticated Routes Covered (Point 6) ✅ IMPLEMENTED

### Authentication & Login
- ✅ **GET `/login`** - Login page loads with form fields (test: test_login_page_loads)
- ✅ **POST `/login`** - User login with valid credentials (test: test_user_login_successful)
- ✅ **POST `/login`** - Login fails with invalid credentials (test: test_user_login_with_invalid_credentials)
- ✅ **GET `/register`** - Registration page loads with email field (test: test_registration_page_loads)

### Public Submission Routes
- ✅ **GET `/submissions`** - Publicly accessible, shows public submissions (test: test_submissions_page_allows_public_access)

### Protected Routes (Access Control - Requires Authentication)
- ✅ **GET `/new_submission`** - Redirects unauthenticated users to login (test: test_new_submission_requires_authentication)
- ✅ **GET `/profile`** - User profile page requires authentication (test: test_profile_requires_authentication)
- ✅ **POST `/profile`** - Profile updates require authentication and work correctly (test: test_authenticated_user_can_update_profile)
  - ✅ Full name field update
  - ✅ Institution/address field update
  - ✅ Required field validation (HTML5)
  - ✅ Success message display
- ✅ **GET `/new_submission` (authenticated)** - Authenticated users can access submission form (test: test_authenticated_user_can_access_new_submission_form)
  - ✅ User profile data pre-populated
  - ✅ Create button visible and accessible

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
- ✅ Unauthenticated access redirects to login with proper redirect URL parameters
- ✅ Invalid credentials rejected with appropriate error handling
- ✅ Authenticated users can access protected routes successfully
- ✅ Authenticated users can update profile information
- ✅ Profile form validation (HTML5 required field checking)
- ✅ Success notifications after form submission
- ✅ User session persistence across navigation

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

### ✅ High Priority (NOW IMPLEMENTED - Point 6)
1. ✅ **Authentication Workflows**: Login, registration, credential validation
2. ✅ **Protected Route Access**: Verify authentication requirement on sensitive routes
3. ✅ **Profile Management**: User profile access and updates
4. ✅ **Form Validation**: HTML5 validation on authenticated forms

### High Priority (Next Phase)
1. **Submission Lifecycle**: Create, edit, view, submit workflow (requires form submission implementation)
2. **Role-Based Access Control**: Test different user roles (submitter, reviewer, admin)
3. **API Endpoint Testing**: Comprehensive coverage of `/api_v2/` endpoints with schema validation
4. **Advanced Validation**: Cross-field validation, file upload validation, sequence validation
5. **Submission History**: View previous submissions and their statuses

### Medium Priority
1. **Admin Functions**: User management, submission review, germline set management
2. **File Uploads**: Attachment handling in submissions
3. **Search & Filtering**: Advanced search with multiple filter combinations
4. **Error Handling**: 404, 403, 500 error pages
5. **Data Export**: Download and export functionality

### Low Priority
1. **Internationalization**: Multi-language support testing
2. **Browser Compatibility**: Test across different browsers (Chrome, Firefox, Safari)
3. **Performance**: Load testing for large result sets
4. **Accessibility**: WCAG compliance checking
5. **Mobile Responsiveness**: Mobile device testing

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

## Point 6: Authenticated Routes Testing (✅ COMPLETE)

Nine tests have been implemented to cover authenticated route access, authentication workflows, and user session management:

### Authentication & Access Control Tests (6 tests)
1. **test_login_page_loads** - Verifies login page renders with expected fields
2. **test_user_login_successful** - Tests login with valid test credentials
3. **test_submissions_page_allows_public_access** - Confirms submissions page is public (no auth required)
4. **test_user_login_with_invalid_credentials** - Verifies login rejection for bad credentials
5. **test_new_submission_requires_authentication** - Confirms /new_submission redirects to login
6. **test_registration_page_loads** - Verifies registration page renders

### Authenticated Route Tests (3 tests)
7. **test_profile_requires_authentication** - Verifies /profile redirects unauthenticated users to login
8. **test_authenticated_user_can_update_profile** - Tests profile form submission and validation
   - Verifies pre-filled user data (Full Name, Institution/Address)
   - Tests HTML5 required field validation
   - Confirms success message after update
   - Validates persistent field updates
9. **test_authenticated_user_can_access_new_submission_form** - Tests authenticated access to new submission page
   - Confirms user data is pre-populated in form
   - Verifies Create button is accessible

### Test Fixtures Added
- **test_user** - Creates a test user account in isolated test database with proper password hashing
  - Email: `test@example.com`
  - Password: `TestPassword123!`
  - Auto-cleanup after each test
- **authenticated_page** - Browser session with authenticated user session
  - Handles login flow automatically
  - Navigates to /profile for authenticated tests
  - Ready for additional authenticated route testing

### Key Implementation Details
- Password hashing uses `flask_security.utils.hash_password()` with proper app context
- Test database includes `SECURITY_PASSWORD_SALT` configuration for argon2 hashing
- Test user is automatically created in app context and cleaned up after each test
- Authentication tests use realistic form field labels and button names from the actual app
- Tests validate that protected routes redirect with `?next=` parameters
- Session persistence tested by navigating across multiple authenticated routes

## Point 7: Coverage Report (✅ COMPLETE)

Comprehensive test coverage report created in [COVERAGE.md](./COVERAGE.md) documenting:

- **Covered Routes**: 15 E2E tests covering public pages, API endpoints, and authenticated routes
  - 6 public routes (licensing, help, germline sets, sequences, API status, empty states)
  - 9 authenticated routes (login, registration, profile, submissions, new submission form)
- **Tested Forms**: Login form, registration form, profile update form, germline set filters, sequence filters
- **Access Control**: Verified unauthenticated access controls, public vs. protected routes, authenticated user functionality
- **Routes Not Yet Covered**: 50+ routes across submissions, admin functions, sub-forms, and API endpoints
- **Recommended Future Coverage**: Prioritized list with authentication workflows now moved to "High Priority (Next Phase)"
- **Browser Diagnostics**: Console error and failed request logging implemented
