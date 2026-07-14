# 00 — Architecture Overview

> **Audit scope**: React frontend only (no backend exists yet).
> Every claim cites source files and line numbers.
> `[MOCK]` = currently backed by localStorage / hardcoded data.
> `[INFERRED]` = behaviour assumed from code patterns rather than explicit docs.

---

## 1. Technology Stack

| Layer          | Library / Tool                                      | Evidence                                                               |
|----------------|------------------------------------------------------|------------------------------------------------------------------------|
| Framework      | React 19 (via Vite)                                  | `package.json`, `vite.config.js`                                       |
| Routing        | react-router-dom v7 (createBrowserRouter)            | `App.jsx:2,9–87`                                                       |
| State          | Redux Toolkit + RTK Query                            | `store/index.js:1–4`, `features/*/...Api.js`                           |
| Persistence    | redux-persist (cart only) + manual localStorage       | `store/index.js:7,11–15`, `api/orders.api.js`, `api/designs.api.js`    |
| Canvas engine  | Konva.js (react-konva) — **primary studio**          | `features/studio/components/StudioCanvas.jsx`                          |
| Canvas engine  | Fabric.js — **legacy studio** (unused in routing)    | `features/design-studio/useStudio.js:3`                                |
| Forms          | react-hook-form + @hookform/resolvers + Zod          | `pages/auth/LoginPage.jsx:2–3`, `utils/validators.js`                  |
| Animation      | framer-motion                                        | `pages/storefront/HomePage.jsx:2`                                      |
| Icons          | lucide-react                                         | used across all pages                                                  |
| Styling        | Tailwind CSS v4                                      | `index.css`, `tailwind.config.js` (absent; v4 uses CSS config)         |
| Image upload   | Cloudinary (optional, with data-URL fallback)        | `hooks/useCloudinary.js:10–12`, `.env:4–5`                             |
| Fonts          | Google Fonts (Montserrat, Outfit, Noto Nastaliq Urdu)| `index.css:2–5`, `features/studio/useUrduFonts.js:3–6`                 |

---

## 2. Directory Layout

```
src/
├── api/                  # Raw API "client" functions (currently all localStorage)
│   ├── auth.api.js       # login/signup/getCurrentUser — [MOCK]
│   ├── designs.api.js    # saveDesign/getDesigns/deleteDesign — [MOCK]
│   └── orders.api.js     # createOrder/getOrders/updateOrderStatus — [MOCK]
│
├── components/
│   ├── atoms/            # Spinner
│   ├── molecules/        # QuantityInput
│   └── organisms/        # AnnouncementBar, SiteHeader, SiteFooter, UspStrip,
│                         #   FilterBar, ProductCard, CartDrawer → relocated
│
├── data/
│   └── products.mock.js  # Hard-coded product catalog (8 products)
│
├── features/
│   ├── auth/authSlice.js     # Redux slice + async thunks for login/signup/logout
│   ├── cart/
│   │   ├── cartSlice.js      # addItem, removeItem, updateQuantity, clearCart
│   │   └── CartDrawer.jsx    # Slide-over cart panel
│   ├── designs/designsApi.js # RTK Query endpoints wrapping designs.api.js [MOCK]
│   ├── orders/ordersApi.js   # RTK Query endpoints wrapping orders.api.js [MOCK]
│   ├── products/
│   │   ├── productsApi.js    # RTK Query — getProducts, getProductBySlug, getProductById [MOCK]
│   │   ├── productsSlice.js  # Simple list store (unused by pages — superseded by RTK Query)
│   │   └── useProducts.js    # Hook wrapper (unused by pages)
│   ├── studio/               # ★ PRIMARY design studio (Konva.js)
│   │   ├── studioSlice.js    # Design model: objects[], background, history, UI state
│   │   ├── useStudio.js      # Action dispatchers (addText, addImage, undo, etc.)
│   │   ├── studioUtils.js    # serializeDesign, deserializeDesign, default print area
│   │   ├── studioHistoryMiddleware.js  # Redux middleware for undo/redo
│   │   ├── useUrduFonts.js   # Google Fonts loader for Nastaliq / Naskh
│   │   └── components/
│   │       ├── StudioShell.jsx          # Top-level shell (toolbar + panels + canvas)
│   │       ├── StudioCanvas.jsx         # react-konva Stage + Layers
│   │       ├── StudioDock.jsx           # Mobile floating toolbar
│   │       ├── StudioPropertiesPanel.jsx# Right-side property editor
│   │       └── ImageUploadButton.jsx    # Cloudinary + data-URL fallback
│   └── design-studio/       # ★ LEGACY studio (Fabric.js) — NOT routed
│       ├── studioSlice.js
│       ├── useStudio.js
│       ├── ImageUploadButton.jsx
│       └── useUrduFonts.js
│
├── hooks/
│   ├── useCloudinary.js      # Cloudinary upload helper
│   ├── useDebounce.js
│   ├── useLocalStorage.js
│   ├── useMediaQuery.js
│   ├── useScrollLock.js      # ⚠ File actually exports useScrolled (name mismatch)
│   ├── useScrolled.js        # Duplicate of useScrollLock.js
│   └── useToast.js           # DOM-based toast notification system
│
├── layouts/
│   ├── MainLayout.jsx        # Storefront shell (header, footer, CartDrawer, Outlet)
│   └── AdminLayout.jsx       # Admin shell (sidebar nav, Outlet)
│
├── pages/
│   ├── auth/
│   │   ├── LoginPage.jsx
│   │   ├── SignupPage.jsx
│   │   └── ForgotPasswordPage.jsx
│   ├── storefront/
│   │   ├── HomePage.jsx
│   │   ├── CollectionPage.jsx
│   │   ├── ProductDetailPage.jsx
│   │   ├── CartPage.jsx
│   │   ├── CheckoutPage.jsx
│   │   └── AccountPage.jsx
│   ├── studio/
│   │   └── DesignStudioPage.jsx
│   └── admin/
│       ├── AdminDashboardPage.jsx
│       ├── AdminOrdersPage.jsx
│       ├── AdminOrderDetails.jsx
│       └── OrderTable.jsx
│
├── utils/
│   ├── cn.js                 # clsx + tailwind-merge wrapper
│   ├── currency.js           # formatPKR() — PKR formatting
│   └── validators.js         # Zod schemas for all forms
│
├── store/index.js            # Redux store config
├── App.jsx                   # Router definition
└── main.jsx                  # Entry point (React root)
```

---

## 3. Routing Map

All routes defined in `App.jsx:9–87` via `createBrowserRouter`.

| Path                         | Component                | Layout       | Guard          |
|------------------------------|--------------------------|--------------|----------------|
| `/`                          | `HomePage`               | `MainLayout` | —              |
| `/collections`               | `CollectionPage`         | `MainLayout` | —              |
| `/products/:slug`            | `ProductDetailPage`      | `MainLayout` | —              |
| `/cart`                       | `CartPage`               | `MainLayout` | —              |
| `/checkout`                   | `CheckoutPage`           | `MainLayout` | —              |
| `/account`                    | `AccountPage`            | `MainLayout` | —              |
| `/studio/:productId`         | `DesignStudioPage`       | —  (full-screen)  | —       |
| `/login`                      | `LoginPage`              | —            | —              |
| `/signup`                     | `SignupPage`             | —            | —              |
| `/forgot-password`            | `ForgotPasswordPage`     | —            | —              |
| `/admin`                      | `AdminDashboardPage`     | `AdminLayout`| `AdminGuard`   |
| `/admin/orders`               | `AdminOrdersPage`        | `AdminLayout`| `AdminGuard`   |
| `/admin/orders/:orderId`      | `AdminOrderDetails`      | `AdminLayout`| `AdminGuard`   |
| `/admin/products`             | placeholder              | `AdminLayout`| `AdminGuard`   |
| `/admin/designs`              | placeholder              | `AdminLayout`| `AdminGuard`   |
| `/admin/customers`            | placeholder              | `AdminLayout`| `AdminGuard`   |
| `/admin/settings`             | placeholder              | `AdminLayout`| `AdminGuard`   |

### Route Guards

- **`AdminGuard`** (`App.jsx:18–28`): Reads `selectIsAuthenticated` and `selectUser` from Redux; if not authenticated redirects to `/login`, if user role ≠ `'admin'` redirects to `/`. Otherwise renders `<Outlet />`.

---

## 4. State Management Architecture

### 4.1 Redux Store (`store/index.js`)

```
rootReducer = {
  auth:       authSlice         // user, token, loading, error
  studio:     studioSlice       // design objects, history, UI state, product context
  cart:       cartSlice         // items array (persisted via redux-persist)
  products:   productsSlice     // legacy list (unused)
  [productsApi.reducerPath]: productsApi.reducer   // RTK Query cache
  [ordersApi.reducerPath]:   ordersApi.reducer     // RTK Query cache
  [designsApi.reducerPath]:  designsApi.reducer    // RTK Query cache
}
```

**Middleware**: Default middleware + `studioHistoryMiddleware` + RTK Query middlewares for `productsApi`, `ordersApi`, `designsApi`.

**Persistence**: Only `cart` slice is persisted via `redux-persist` using `localStorage` with key `'persist:frill-cart'` (`store/index.js:11–15`).

### 4.2 Auth State (`features/auth/authSlice.js`)

- `loginUser` async thunk → calls `api/auth.api.js:login()` → **[MOCK]** base64-encodes user as JWT, stores in `localStorage['frill_token']`
- `signupUser` async thunk → calls `api/auth.api.js:signup()` → **[MOCK]** appends to `localStorage['frill_users']` array
- `loadSession` async thunk → calls `api/auth.api.js:getCurrentUser()` → **[MOCK]** reads token from localStorage
- `logout` reducer → clears token from localStorage
- Selectors: `selectUser`, `selectIsAuthenticated`, `selectAuthLoading`, `selectAuthError`

### 4.3 Cart State (`features/cart/cartSlice.js`)

- `addItem` → Generates composite key `{productId}-{colorId}-{viewId}-{size}-{designId?}` (`cartSlice.js:19–24`)
- `removeItem`, `updateQuantity`, `clearCart`
- Selectors: `selectCartItems`, `selectCartCount`, `selectCartTotal`
- Each cart item stores: `key, productId, name, img, price, quantity, selectedSize, selectedColor, selectedColorName, selectedViewLabel, mockupUrl, printUrl, designJson, designId`

### 4.4 Studio State (`features/studio/studioSlice.js`)

This is the most complex slice. Key shape:

```js
{
  design: {
    objects: [],           // Array of design elements (text, image, shape, line)
    background: {
      imageUrl, color, viewId, viewLabel, printArea: { x, y, width, height }
    }
  },
  history: {
    past: [],              // Array of serialized design snapshots
    future: [],            // For redo
  },
  ui: {
    tool: 'select',        // 'select' | 'text' | 'image' | 'shape' | 'brush'
    selectedObjectId: null,
    zoom: 1,
    snapping: true,
    brush: { color: '#000000', size: 4 },
  },
  productContext: {
    id, name, colorId, colorName, colorHex, price
  }
}
```

- **History middleware** (`studioHistoryMiddleware.js`): Intercepts design-mutating actions, pushes snapshots to `history.past`, clears `history.future`.

### 4.5 RTK Query APIs

All three RTK Query APIs use `queryFn` (no `baseQuery`) since they wrap localStorage:

| API              | File                           | Endpoints                                              |
|------------------|--------------------------------|--------------------------------------------------------|
| `productsApi`    | `features/products/productsApi.js` | `getProducts({category, sort, search})`, `getProductBySlug({slug})`, `getProductById({id})` |
| `ordersApi`      | `features/orders/ordersApi.js`     | `getOrders()`, `createOrder(body)` (mutation)          |
| `designsApi`     | `features/designs/designsApi.js`   | `getDesigns()`, `saveDesign(body)` (mutation), `deleteDesign({id})` (mutation) |

---

## 5. Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        BROWSER / CLIENT                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   React Pages ──→ dispatch() ──→ Redux Store                    │
│      │                              │                            │
│      │  useSelector()  ←────────────┘                            │
│      │                                                           │
│      ├── Auth thunks ──→ api/auth.api.js ──→ [MOCK] localStorage│
│      │                                                           │
│      ├── RTK Query:                                              │
│      │   productsApi ──→ PRODUCTS_MOCK (hardcoded array)         │
│      │   ordersApi   ──→ api/orders.api.js ──→ localStorage     │
│      │   designsApi  ──→ api/designs.api.js ──→ localStorage    │
│      │                                                           │
│      ├── Cart slice  ──→ redux-persist ──→ localStorage          │
│      │                                                           │
│      └── Studio:                                                 │
│          StudioShell ──→ studioSlice (Redux)                     │
│          StudioCanvas ──→ Konva Stage (imperative rendering)     │
│          Export: stage.toDataURL() → mockup/print PNGs           │
│          Confirm: serializeDesign() → designJson → cart item     │
│                                                                  │
│   External calls:                                                │
│      useCloudinary ──→ Cloudinary API (optional image upload)    │
│      useUrduFonts  ──→ Google Fonts CDN (font loading)           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Mock / Fake Boundaries

Every data persistence path currently terminates at `localStorage` or hardcoded data:

| Boundary                            | Mechanism                                             | Key / Location                       |
|--------------------------------------|-------------------------------------------------------|--------------------------------------|
| Products catalog                     | Hardcoded `PRODUCTS_MOCK` array                       | `data/products.mock.js`              |
| User accounts                        | `localStorage['frill_users']` (JSON array)            | `api/auth.api.js:9`                  |
| Auth token                           | `localStorage['frill_token']` (base64 JSON)           | `api/auth.api.js:5,25`               |
| Orders                               | `localStorage['frill_orders']` (JSON array)           | `api/orders.api.js:1`                |
| Designs                              | `localStorage['frill_designs_v2']` (JSON array)       | `api/designs.api.js:1`               |
| Cart                                 | `localStorage['persist:frill-cart']` (redux-persist)  | `store/index.js:13`                  |
| Image uploads                        | Cloudinary API (real, but optional) or data URL fallback | `hooks/useCloudinary.js`          |
| KPI data on admin dashboard          | Hardcoded constants                                   | `pages/admin/AdminDashboardPage.jsx:8–13` |

---

## 7. Key Observations

1. **Dual design studio**: There are TWO complete studio implementations — `features/studio/` (Konva, active) and `features/design-studio/` (Fabric.js, legacy/unused). Only the Konva studio is wired into the router.

2. **File naming issue**: `hooks/useScrollLock.js` exports `useScrolled()` (not `useScrollLock`). There is also `hooks/useScrolled.js` with identical content. Both are identical duplicates.

3. **productsSlice is dead code**: `features/products/productsSlice.js` and `features/products/useProducts.js` exist but are superseded by `productsApi.js` (RTK Query). No page or component imports them.

4. **No real authentication**: Auth is entirely mocked — base64 encoding a JSON object as a "JWT" (`auth.api.js:25`). No token validation, no expiry, no refresh flow.

5. **Social login buttons are decorative**: `LoginPage.jsx:170–178` and `SignupPage.jsx:288–296` render social login icons (Globe, CircleUserRound, Sparkles) with no onClick handlers.

6. **ForgotPasswordPage is a shell**: Form `onSubmit` calls `e.preventDefault()` (`ForgotPasswordPage.jsx:28`) — no actual email sending logic.

7. **Account page "Addresses" and "Settings" tabs render nothing**: `AccountPage.jsx:109–114` — buttons exist but no tab content is wired.

8. **Admin pages for Products, Designs, Customers, Settings are placeholder routes**: `App.jsx` defines routes for them but the components render stub content.

9. **Order status advance uses case-sensitive mismatch**: `AdminOrdersPage.jsx:7` defines lowercase statuses `['pending', 'processing', 'shipped', 'delivered']`, but `OrderTable.jsx:7–14` defines `STATUS_COLORS` with Capitalized keys like `'Pending'`, `'Delivered'`. The `.status !== 'Delivered'` check at `OrderTable.jsx:105` uses capitalized form, while `advanceStatus()` writes lowercase.

10. **Checkout does not require authentication**: Any visitor can place an order. The checkout form collects contact info independent of any logged-in user.
