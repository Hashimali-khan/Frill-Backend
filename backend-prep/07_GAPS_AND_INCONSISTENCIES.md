# 07 — Gaps & Inconsistencies

> Bugs, dead code, naming issues, and design concerns found during the audit.
> Each item is graded: 🔴 Bug, 🟡 Warning, 🔵 Info/Cleanup.

---

## 🔴 Bugs

### B1: Order status case mismatch

**Files**: `AdminOrdersPage.jsx:7` vs `OrderTable.jsx:7–14,105`

`AdminOrdersPage.jsx` defines the pipeline with **lowercase** values:
```js
const STATUS_PIPELINE = ['pending', 'processing', 'shipped', 'delivered']
```

`OrderTable.jsx` defines `STATUS_COLORS` with **Capitalized** keys:
```js
const STATUS_COLORS = {
  Pending: '...', Confirmed: '...', Printing: '...', Dispatched: '...', Delivered: '...',
  Processing: '...', Shipped: '...',
}
```

The advance button check at `OrderTable.jsx:105`:
```js
order.status !== 'Delivered'
```
will never match if statuses are stored lowercase. The status badge will also fail to match colors because `STATUS_COLORS['pending']` is `undefined` (key is `'Pending'`).

**Impact**: Status colors don't render; advance button may show on already-delivered orders.

---

### B2: Checkout error handling is silent

**File**: `CheckoutPage.jsx:112–117`

On order creation failure, the error is caught but the user still sees a success screen:
```js
.catch((err) => {
  console.error('Failed to save order:', err)
  // Still show success message but note was not saved
  setSubmittedOrder(finalOrder)
  dispatch(clearCart())
})
```

**Impact**: User thinks order was placed successfully when it may have failed. Cart is cleared either way.

---

### B3: ForgotPasswordPage form does nothing

**File**: `ForgotPasswordPage.jsx:28`

```js
<form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
```

The form prevents default and does nothing else. No API call, no success message, no state change.

**Impact**: Users who forget passwords have no recovery path.

---

## 🟡 Warnings

### W1: No `userId` on orders

**Files**: `CheckoutPage.jsx:98–103`, `api/orders.api.js:3–13`

Orders are created without any user association:
```js
const finalOrder = { ...mergedData, items, count, total }
```

No `userId`, `customerId`, or session reference is included. `AccountPage.jsx:26` comments: "For now, show all orders (in production, filter by user.id)."

**Impact**: Cannot filter orders by customer; all users see all orders.

---

### W2: No `userId` on saved designs

**File**: `api/designs.api.js:3–12`

Similar to orders — designs are saved without user association.

**Impact**: Cannot implement user-scoped design galleries.

---

### W3: Canvas export CORS failures silently succeed

**File**: `StudioShell.jsx:156–170`

When the canvas is "tainted" by cross-origin images (e.g., Cloudinary URLs), the export returns `{ printUrl: null, mockupUrl: null }` but the cart item is still added:

```js
return { printUrl: null, mockupUrl: null }
```

The user receives no warning that their design won't have preview images.

**Impact**: Orders may arrive without mockup/print images, making production difficult.

---

### W4: Data URLs in cart/orders can exceed localStorage limits

**Files**: `StudioShell.jsx:194–195`, `store/index.js:11–15`

Canvas exports at 3x resolution generate large base64 strings. These are stored in:
1. Cart items (redux-persist → localStorage)
2. Order records (localStorage)

`localStorage` has a ~5–10 MB limit per origin. A single design with a 3x export can use 2–5 MB.

**Impact**: Multiple custom designs in cart can cause `QuotaExceededError`, silently failing to persist cart or orders.

---

### W5: AdminGuard is client-side only

**File**: `App.jsx:18–28`

Admin protection relies solely on Redux state. There is no server-side role verification. A user can:
1. Manually set `role: 'admin'` in localStorage
2. Decode and re-encode the base64 "token" with `role: 'admin'`
3. Access all admin routes

**Impact**: Complete authorization bypass in current implementation.

---

### W6: `AccountPage` mixes RTK Query and direct API calls

**Files**: `AccountPage.jsx:8,25` vs `AdminDashboardPage.jsx:26`

`AccountPage` imports `getOrders` directly from `api/orders.api.js` and calls it imperatively. `AdminDashboardPage` uses `useGetOrdersQuery()` from RTK Query for the same data.

**Impact**: Two caching strategies for the same data. RTK Query cache and manual state can drift.

---

### W7: `AdminOrdersPage` also uses direct API calls

**File**: `AdminOrdersPage.jsx:3,28,46`

Imports both `getOrders` and `updateOrderStatus` from `api/orders.api.js` directly instead of using RTK Query mutations.

**Impact**: After status update, must manually re-fetch. RTK Query cache is not invalidated.

---

### W8: Hardcoded KPI data

**File**: `AdminDashboardPage.jsx:8–13`

```js
const KPI_CARDS = [
  { label: 'Total Revenue', value: 248500, ... },
  { label: 'Orders Today',  value: 17, ... },
  // ...
]
```

These numbers are completely static regardless of actual order data.

**Impact**: Admin dashboard shows misleading statistics.

---

## 🔵 Info / Cleanup

### I1: Dual design studio implementations

**Files**: `features/studio/` (Konva, active) vs `features/design-studio/` (Fabric.js, unused)

The Fabric.js studio (`features/design-studio/`) is not referenced by any route or page. It includes:
- `studioSlice.js` (78 lines) — conflicts with `features/studio/studioSlice.js` namespace
- `useStudio.js` (502 lines)
- `ImageUploadButton.jsx` (73 lines)
- `useUrduFonts.js` (31 lines) — identical to `features/studio/useUrduFonts.js`

**Recommendation**: Delete `features/design-studio/` entirely.

---

### I2: `useScrollLock.js` / `useScrolled.js` duplicate

**Files**: `hooks/useScrollLock.js`, `hooks/useScrolled.js`

Both files are **byte-for-byte identical**. Both export `useScrolled()`. The filename `useScrollLock.js` is misleading — it has nothing to do with scroll locking.

**Recommendation**: Delete one, rename or keep the other.

---

### I3: `productsSlice.js` and `useProducts.js` are dead code

**Files**: `features/products/productsSlice.js`, `features/products/useProducts.js`

These were superseded by `productsApi.js` (RTK Query). The `products` slice is still in the store reducer (`store/index.js`) but no component dispatches `setProducts` or reads `state.products.list`.

**Recommendation**: Remove from store and delete files.

---

### I4: Social login buttons have no functionality

**Files**: `LoginPage.jsx:170–178`, `SignupPage.jsx:288–296`

Three icon buttons (Globe, CircleUserRound, Sparkles) are rendered with no click handlers, no OAuth setup, and no tooltips indicating they are coming soon.

**Recommendation**: Either implement OAuth or add "Coming Soon" tooltips / disabled state.

---

### I5: `VITE_API_URL` is set but never used

**Files**: `.env:1`, `.env.example:2`

```
VITE_API_URL=https://api.example.com
```

No code in `src/` references `import.meta.env.VITE_API_URL`. All API calls go through mock localStorage functions.

**Recommendation**: Will be used when real API is integrated. Consider using it as `baseQuery` URL for RTK Query.

---

### I6: Payment gateway env vars defined but unused

**File**: `.env.example:11–12`

```
VITE_JAZZCASH_MERCHANT_ID=your_merchant_id
VITE_EASYPAISA_STORE_ID=your_store_id
```

No code references these variables. JazzCash and Easypaisa integration is limited to collecting a wallet number in the checkout form.

---

### I7: Account page tabs for "Addresses" and "Settings" are unimplemented

**File**: `AccountPage.jsx:109–114`

Sidebar buttons exist for "Addresses" and "Settings" tabs but clicking them does nothing (no `onClick` handlers set `activeTab`).

---

### I8: Admin sidebar nav items for Products, Designs, Customers, Settings are placeholders

**File**: `AdminLayout.jsx:12–16`, `App.jsx:82–85`

Routes are defined and sidebar links work, but the page components render minimal placeholder content.

---

### I9: `HomePage.jsx` imports `PRODUCTS_MOCK` directly

**File**: `HomePage.jsx:15,58`

```js
import { PRODUCTS_MOCK } from '@/data/products.mock'
const TRENDING_PRODUCTS = PRODUCTS_MOCK.slice(0, 4)
```

This bypasses RTK Query and directly imports the mock data. When products move to the database, this import path breaks.

**Recommendation**: Use `useGetProductsQuery()` with a limit/featured filter.
