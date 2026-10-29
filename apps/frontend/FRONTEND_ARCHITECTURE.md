# Frontend Architecture

## Runtime and boundaries

The user interface is plain HTML5, CSS3, and native ES modules. `index.html` is the entry point; `server.mjs` is a small static development server and same-origin API proxy. There is no bundler, frontend framework, external component library, or separate data store. All persistent business data is read or changed through the existing Django REST API. The browser never connects to MySQL.

## Modules

- `src/app.js` owns hash navigation, role-aware page selection, the shared shell, pages, and delegated interaction handlers. The URL hash supports public, customer, staff, and administration pages; branch selection uses a query string in the hash.
- `src/api.js` centralizes Fetch, JSON encoding/decoding, timeout/network errors, bearer headers, API base URL, and status-aware error handling. `index.html` sets `meta[name="api-base"]`; the default is `/api`.
- `src/auth.js` owns login, registration, current-user lookup, logout, and JWT expiry. The access token and user are held in JavaScript memory only. A page reload requires sign-in again. No refresh token is assumed or invented.
- `src/ui.js` provides escaped HTML output, buttons, fields, tables, cards, empty states, headings, and monetary formatting.
- `styles.css` defines the shared pharmacy theme, responsive layouts, focus states, tables, forms, dialog editing, and checkout/order summaries.
- `tests/api.test.mjs` uses Node's built-in test runner to check the isolated API client without a database or network.

## Data flow and security

Page functions request current API data when rendered. The catalog reads listed stock and branch prices from `/pharmacies/{id}/inventory/`; the selected pharmacy can be changed, and items without positive listed stock cannot be added from a catalog card. Mutation handlers await the server response before showing success and re-render the affected page. Checkout first requests `/checkout/quote/`, displays the server-calculated lines and totals, then sends `/api/orders/` only after the customer confirms. The place-order request includes the quoted unit prices and total; the backend validates them again under its transaction rules.

Customer, staff, and admin navigation follows the role and pharmacy assignments returned by `/api/me/`. UI restrictions improve usability only; the backend remains the authority and its 401 and 403 responses are presented distinctly. Username prefixes do not affect access. Payment and shipment are explicitly simulated; the UI does not request card numbers, security codes, or cryptocurrency secrets.

Guest cart operations use the backend guest-cart endpoint and its same-origin cookie. Customer cart operations use `/api/cart/`. No static catalogue, product, pharmacy, user, order, price, or stock data is used as a substitute for API data.

## Navigation and accessibility

The application uses simple hash navigation and native anchors/forms. Shared shell navigation has a mobile toggle. Pages include loading/error/empty states, form labels, required/type constraints, keyboard focus styling, and native `<dialog>` for editing admin records. Data values inserted into HTML are escaped by `ui.js`.

## API contract limitations

The current API does not provide a public promotions list, a staff qualification field in the assignment list, a cart merge operation, or delete operations for general admin resources. The frontend does not simulate these. Prescription verification is shown only when `/api/me/` reports pharmacist qualification; the server can still reject an order without a prescription with a validation/conflict response.

The live catalogue currently returns three `DEMO-*` synthetic seed records. The frontend displays exactly what the API returns and does not represent those rows as a real pharmaceutical catalogue. Route rendering resets scroll for navigation and ignores stale responses from superseded route renders.
