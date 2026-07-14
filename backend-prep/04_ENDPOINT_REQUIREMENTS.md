# 04 — Endpoint Requirements

> Every API endpoint the frontend currently needs or will need.
> Derived from actual function calls, RTK Query definitions, and page logic.
> Does **NOT** design the backend — only documents what the frontend expects.

---

## Notation

- **Method**: HTTP verb the frontend expects
- **Current impl**: Where the call currently resolves (all `[MOCK]`)
- **Request body / params**: Exact shape the frontend sends
- **Response shape**: What the frontend code expects to receive
- **Auth**: Whether the call requires authentication
- **Priority**: P0 = must-have for MVP, P1 = needed for full feature, P2 = nice-to-have

---

## 1. Authentication

### POST `/auth/signup`

| Field | Value |
|-------|-------|
| Current impl | `api/auth.api.js:signup()` → localStorage `frill_users` |
| Called from | `authSlice.js:loginUser` thunk ← `SignupPage.jsx:38` |
| Request body | `{ firstName, lastName, email, phone, password }` |
| Response | `{ user: { id, firstName, lastName, email, phone, role }, token: string }` |
| Auth | No |
| Priority | **P0** |

### POST `/auth/login`

| Field | Value |
|-------|-------|
| Current impl | `api/auth.api.js:login()` → scans `frill_users` |
| Called from | `authSlice.js:signupUser` thunk ← `LoginPage.jsx:33` |
| Request body | `{ email, password }` |
| Response | `{ user: { id, firstName, lastName, email, phone, role }, token: string }` |
| Auth | No |
| Priority | **P0** |

### GET `/auth/me`

| Field | Value |
|-------|-------|
| Current impl | `api/auth.api.js:getCurrentUser()` → decodes base64 token |
| Called from | `authSlice.js:loadSession` thunk |
| Request body | None (token in Authorization header) |
| Response | `{ user: { id, firstName, lastName, email, phone, role } }` |
| Auth | Yes (Bearer token) |
| Priority | **P0** |

### POST `/auth/logout`

| Field | Value |
|-------|-------|
| Current impl | `authSlice.js:logout` reducer → clears `frill_token` from localStorage |
| Called from | `SiteHeader.jsx`, `AdminLayout.jsx:23–26` |
| Request body | None |
| Response | `{ success: true }` |
| Auth | Yes |
| Priority | **P0** |

### POST `/auth/forgot-password`

| Field | Value |
|-------|-------|
| Current impl | **NONE** — `ForgotPasswordPage.jsx:28` does `e.preventDefault()` only |
| Called from | `ForgotPasswordPage.jsx` (not yet wired) |
| Request body | `{ email }` |
| Response | `{ message: string }` |
| Auth | No |
| Priority | **P1** |

### POST `/auth/reset-password`

| Field | Value |
|-------|-------|
| Current impl | **NONE** — no UI or code exists |
| Called from | Future page |
| Request body | `{ token, newPassword }` |
| Response | `{ success: true }` |
| Auth | No (token in body) |
| Priority | **P1** |

---

## 2. Products

### GET `/api/products`

| Field | Value |
|-------|-------|
| Current impl | `productsApi.js:getProducts` queryFn → filters `PRODUCTS_MOCK` |
| Called from | `CollectionPage.jsx:10`, `DesignStudioPage.jsx:11`, `HomePage.jsx:58` (direct import) |
| Query params | `?category=string&sort=price-asc|price-desc|name-az|name-za&q=string` |
| Response | `Product[]` (see 01_DATA_MODELS.md §2) |
| Auth | No |
| Priority | **P0** |

**Filtering logic** (from `productsApi.js:12–27`):
- `category`: exact match on `product.category`
- `sort`: `price-asc`, `price-desc`, `name-az`, `name-za`
- `search` (`q`): case-insensitive `includes` on `product.name`

### GET `/api/products/:slug`

| Field | Value |
|-------|-------|
| Current impl | `productsApi.js:getProductBySlug` queryFn → `PRODUCTS_MOCK.find(p => p.slug === slug)` |
| Called from | `ProductDetailPage.jsx:18` |
| Response | `Product` (single) or `null` |
| Auth | No |
| Priority | **P0** |

### GET `/api/products/:id`

| Field | Value |
|-------|-------|
| Current impl | `productsApi.js:getProductById` queryFn → `PRODUCTS_MOCK.find(p => p.id === id)` |
| Called from | `DesignStudioPage.jsx:12` |
| Response | `Product` (single) or `null` |
| Auth | No |
| Priority | **P0** |

**Note**: In the current mock, `id === slug`. Backend may want to use a UUID for `id` and keep `slug` as a human-readable URL identifier. If so, the `getProductById` and `getProductBySlug` endpoints become distinct.

---

## 3. Orders

### POST `/api/orders`

| Field | Value |
|-------|-------|
| Current impl | `ordersApi.js:createOrder` mutation → `api/orders.api.js:createOrder()` → localStorage |
| Called from | `CheckoutPage.jsx:106` |
| Request body | See below |
| Response | `Order` (with server-assigned `id`, `status`, `createdAt`) |
| Auth | **Currently no** — checkout is anonymous. Backend should optionally attach `userId` if authenticated. |
| Priority | **P0** |

**Request body shape** (from `CheckoutPage.jsx:98–103`):
```json
{
  "firstName": "string",
  "lastName": "string",
  "email": "string",
  "phone": "string",
  "address": "string",
  "city": "string",
  "province": "string",
  "postalCode": "string",
  "paymentMethod": "cod | jazzcash | easypaisa",
  "walletNumber": "string | ''",
  "items": [CartItem],
  "count": "number",
  "total": "number"
}
```

### GET `/api/orders`

| Field | Value |
|-------|-------|
| Current impl | `ordersApi.js:getOrders` query → `api/orders.api.js:getOrders()` → returns ALL orders |
| Called from | `AdminDashboardPage.jsx:26`, `AdminOrdersPage.jsx:28`, `AccountPage.jsx:25` |
| Query params | None currently. Needs: `?userId=X` (for account page), `?status=X` (optional server-side), `?limit=N&offset=M` (pagination) |
| Response | `Order[]` |
| Auth | Yes (admin: all orders; customer: own orders only) |
| Priority | **P0** |

### GET `/api/orders/:id`

| Field | Value |
|-------|-------|
| Current impl | `AdminOrderDetails.jsx:8` — finds in RTK Query cache (no dedicated endpoint) |
| Called from | `AdminOrderDetails.jsx:6–8` |
| Response | `Order` (single) |
| Auth | Yes (admin or order owner) |
| Priority | **P0** |

### PATCH `/api/orders/:id/status`

| Field | Value |
|-------|-------|
| Current impl | `api/orders.api.js:updateOrderStatus(orderId, status)` → patches localStorage |
| Called from | `AdminOrdersPage.jsx:46` |
| Request body | `{ status: "pending" | "processing" | "shipped" | "delivered" }` |
| Response | `Order` (updated) |
| Auth | Yes (admin only) |
| Priority | **P0** |

---

## 4. Designs

### GET `/api/designs`

| Field | Value |
|-------|-------|
| Current impl | `designsApi.js:getDesigns` query → `api/designs.api.js:getDesigns()` → localStorage |
| Called from | Not currently called from any page (admin designs page is placeholder) |
| Query params | Needs: `?userId=X` for user's own designs |
| Response | `SavedDesign[]` |
| Auth | Yes (user sees own; admin sees all) |
| Priority | **P1** |

### POST `/api/designs`

| Field | Value |
|-------|-------|
| Current impl | `designsApi.js:saveDesign` mutation → `api/designs.api.js:saveDesign()` → localStorage |
| Called from | Not currently called from any page |
| Request body | `{ name, designJson, productId, colorId, viewId, mockupUrl }` |
| Response | `SavedDesign` (with server-assigned `id`, `createdAt`) |
| Auth | Yes |
| Priority | **P1** |

### DELETE `/api/designs/:id`

| Field | Value |
|-------|-------|
| Current impl | `designsApi.js:deleteDesign` mutation → `api/designs.api.js:deleteDesign()` → localStorage |
| Called from | Not currently called from any page |
| Response | `{ success: true }` |
| Auth | Yes (owner or admin) |
| Priority | **P1** |

---

## 5. Media Upload

### POST `/api/upload/image`

| Field | Value |
|-------|-------|
| Current impl | `hooks/useCloudinary.js` → direct Cloudinary API call (bypasses backend) |
| Called from | `ImageUploadButton.jsx` (both studio versions) |
| Request body | `multipart/form-data` with `file` field |
| Response | `{ url: "https://..." }` (CDN URL of uploaded image) |
| Auth | [INFERRED] Yes — should be authenticated to prevent abuse |
| Priority | **P0** |

**Note**: Currently the frontend uploads directly to Cloudinary using unsigned presets. For production with Supabase Storage, the backend should provide a signed upload URL or proxy the upload.

### POST `/api/upload/design-export`

| Field | Value |
|-------|-------|
| Current impl | **NONE** — PNGs are stored as data URLs in cart items |
| Called from | `StudioShell.jsx:146,150` generates `printUrl` and `mockupUrl` as data URLs |
| Request body | `multipart/form-data` with `mockup` (1x PNG) and `print` (3x PNG) |
| Response | `{ mockupUrl: "https://...", printUrl: "https://..." }` |
| Auth | Yes |
| Priority | **P0** |

**Note**: Currently the canvas exports are base64 data URLs stored directly in cart state and eventually in the order. These can be several MB each. The backend should accept the export PNGs and return CDN URLs.

---

## 6. Admin Stats (Future)

### GET `/api/admin/stats`

| Field | Value |
|-------|-------|
| Current impl | Hardcoded constants in `AdminDashboardPage.jsx:8–13` |
| Called from | `AdminDashboardPage.jsx` |
| Response | `{ totalRevenue, ordersToday, activeProducts, totalCustomers, deltas: {...} }` |
| Auth | Yes (admin only) |
| Priority | **P2** |

---

## 7. User Profile (Future)

### GET `/api/users/me`

| Field | Value |
|-------|-------|
| Current impl | Auth state from Redux (no separate profile endpoint) |
| Called from | `AccountPage.jsx:11` reads from `selectUser` |
| Response | `User` (full profile with addresses) |
| Auth | Yes |
| Priority | **P1** |

### PUT `/api/users/me`

| Field | Value |
|-------|-------|
| Current impl | **NONE** — "Edit Profile" button has no handler (`AccountPage.jsx:179`) |
| Called from | Future |
| Request body | `{ firstName?, lastName?, phone?, ... }` |
| Response | `User` (updated) |
| Auth | Yes |
| Priority | **P1** |

---

## Summary: Endpoint Priority Matrix

| Priority | Endpoint | Domain |
|----------|----------|--------|
| **P0** | POST `/auth/signup` | Auth |
| **P0** | POST `/auth/login` | Auth |
| **P0** | GET `/auth/me` | Auth |
| **P0** | POST `/auth/logout` | Auth |
| **P0** | GET `/api/products` | Products |
| **P0** | GET `/api/products/:slug` | Products |
| **P0** | GET `/api/products/:id` | Products |
| **P0** | POST `/api/orders` | Orders |
| **P0** | GET `/api/orders` | Orders |
| **P0** | GET `/api/orders/:id` | Orders |
| **P0** | PATCH `/api/orders/:id/status` | Orders |
| **P0** | POST `/api/upload/image` | Media |
| **P0** | POST `/api/upload/design-export` | Media |
| **P1** | POST `/auth/forgot-password` | Auth |
| **P1** | POST `/auth/reset-password` | Auth |
| **P1** | GET `/api/designs` | Designs |
| **P1** | POST `/api/designs` | Designs |
| **P1** | DELETE `/api/designs/:id` | Designs |
| **P1** | GET `/api/users/me` | Users |
| **P1** | PUT `/api/users/me` | Users |
| **P2** | GET `/api/admin/stats` | Admin |
