# 02 — Module Inventory

> File-by-file inventory of every `.js` / `.jsx` module in `src/`.
> Each entry states: purpose, imports, exports, mock boundaries, and backend relevance.

---

## Entry Point & Config

### `main.jsx`
- **Purpose**: React 19 app bootstrap.
- **Key lines**: Creates root with `ReactDOM.createRoot()` (line 5), renders `<Provider store={store}><PersistGate><App /></PersistGate></Provider>`.
- **Backend relevance**: None — pure client bootstrap.

### `App.jsx`
- **Purpose**: Route definitions via `createBrowserRouter` (lines 9–87), `AdminGuard` component (lines 18–28).
- **Exports**: Default `App` component.
- **Backend relevance**: `AdminGuard` (line 18–28) reads `selectIsAuthenticated` and `selectUser().role` from Redux. Will need server-side role validation on admin API endpoints.

---

## Store

### `store/index.js`
- **Purpose**: Redux store configuration. Combines `auth`, `studio`, `cart`, `products`, and three RTK Query reducers. Configures `redux-persist` for cart only (`key: 'persist:frill-cart'`).
- **Middleware**: `studioHistoryMiddleware` + RTK Query middlewares.
- **Backend relevance**: When real API is added, RTK Query `baseQuery` will point to FastAPI. Cart persistence may remain client-side.

---

## API Layer (all `[MOCK]`)

### `api/auth.api.js`
- **Purpose**: Login, signup, getCurrentUser — all backed by localStorage.
- **Key constants**: `STORAGE_KEY = 'frill_token'` (line 5), `USERS_KEY = 'frill_users'` (line 9).
- **Functions**:
  - `login({ email, password })` → scans `frill_users`, returns fake JWT (line 25–30)
  - `signup({ firstName, lastName, email, phone, password })` → appends user to array, returns fake JWT (line 14–22)
  - `getCurrentUser()` → decodes base64 token (line 40–52)
- **Backend relevance**: **REPLACE ENTIRELY** with Supabase Auth calls.

### `api/orders.api.js`
- **Purpose**: CRUD for orders in localStorage.
- **Key constant**: `ORDERS_KEY = 'frill_orders'` (line 1).
- **Functions**:
  - `createOrder(orderData)` → assigns `ORD-${Date.now()}` ID, status='pending' (line 3–13)
  - `getOrders()` → returns all orders (line 15–18)
  - `updateOrderStatus(orderId, status)` → patches status (line 21–27)
- **Backend relevance**: **REPLACE ENTIRELY** with FastAPI endpoints + Supabase DB.

### `api/designs.api.js`
- **Purpose**: CRUD for saved designs in localStorage.
- **Key constant**: `DESIGNS_KEY = 'frill_designs_v2'` (line 1).
- **Functions**:
  - `saveDesign(designData)` → assigns `design-${Date.now()}` ID (line 3–12)
  - `getDesigns()` → returns all (line 14–17)
  - `deleteDesign(id)` → filters by ID (line 19–22)
- **Backend relevance**: **REPLACE ENTIRELY** with FastAPI endpoints + Supabase Storage for design assets.

---

## RTK Query APIs

### `features/products/productsApi.js`
- **Purpose**: RTK Query product endpoints using `queryFn` pattern wrapping `PRODUCTS_MOCK`.
- **Endpoints**: `getProducts({category, sort, search})`, `getProductBySlug({slug})`, `getProductById({id})`
- **Backend relevance**: Switch to `baseQuery: fetchBaseQuery({ baseUrl: '/api' })` with real endpoints.

### `features/orders/ordersApi.js`
- **Purpose**: RTK Query order endpoints wrapping `api/orders.api.js`.
- **Endpoints**: `getOrders()` (query), `createOrder(body)` (mutation)
- **Backend relevance**: Switch to real fetch-based endpoints.

### `features/designs/designsApi.js`
- **Purpose**: RTK Query design endpoints wrapping `api/designs.api.js`.
- **Endpoints**: `getDesigns()` (query), `saveDesign(body)` (mutation), `deleteDesign({id})` (mutation)
- **Backend relevance**: Switch to real fetch-based endpoints.

---

## Redux Slices

### `features/auth/authSlice.js`
- **Purpose**: Auth state management with async thunks.
- **Thunks**: `loginUser`, `signupUser`, `loadSession`
- **Reducers**: `logout` (clears token)
- **Selectors**: `selectUser`, `selectIsAuthenticated`, `selectAuthLoading`, `selectAuthError`
- **Backend relevance**: Thunks must call Supabase Auth instead of mock functions.

### `features/cart/cartSlice.js`
- **Purpose**: Cart state with redux-persist.
- **Reducers**: `addItem`, `removeItem`, `updateQuantity`, `clearCart`, `openCart`, `closeCart`
- **Selectors**: `selectCartItems`, `selectCartCount`, `selectCartTotal`, `selectCartOpen`
- **Backend relevance**: Cart may remain client-side (localStorage), or optionally sync to server for logged-in users.

### `features/studio/studioSlice.js`
- **Purpose**: Most complex slice — design model, history, UI state, product context.
- **Reducers**: `addObject`, `updateObject`, `removeObject`, `setSelectedObject`, `setBackground`, `setProductContext`, `setTool`, `setBrush`, `setZoom`, `setSnapping`, `commitHistory`, `undo`, `redo`, `loadDesign`, `resetDesign`
- **Selectors**: `selectDesign`, `selectObjects`, `selectSelectedObject`, `selectBackground`, `selectUiState`, `selectCanUndo`, `selectCanRedo`, `selectProductContext`
- **Backend relevance**: Design save/load will need server endpoints. The slice itself stays client-side.

### `features/studio/studioHistoryMiddleware.js`
- **Purpose**: Intercepts design-mutating actions, calls `commitHistory()`.
- **Backend relevance**: None — stays client-side.

### `features/products/productsSlice.js`
- **Purpose**: Legacy products slice with `setProducts` reducer.
- **Status**: **DEAD CODE** — no page or component imports it.
- **Backend relevance**: Can be deleted.

### `features/products/useProducts.js`
- **Purpose**: Simple selector hook for the legacy productsSlice.
- **Status**: **DEAD CODE**.
- **Backend relevance**: Can be deleted.

---

## Studio Utilities

### `features/studio/studioUtils.js`
- **Purpose**: Serialization/deserialization, default print area, object defaults.
- **Exports**: `serializeDesign()`, `deserializeDesign()`, `DEFAULT_PRINT_AREA`, `createDefaultObject()`
- **Backend relevance**: `serializeDesign()` output is what gets stored on the server.

### `features/studio/useStudio.js`
- **Purpose**: Hook providing design action dispatchers.
- **Exports**: `useStudioActions()` — returns `{ addText, addUrduText, addImage, addRectangle, addCircle, deleteSelected, setTool, setBrush, undo, redo }`
- **Backend relevance**: Client-only actions.

### `features/studio/useUrduFonts.js`
- **Purpose**: Injects Google Fonts `<link>` tags for Urdu fonts, awaits font load.
- **Backend relevance**: None — client-side font loading.

---

## Studio Components

### `features/studio/components/StudioShell.jsx` (536 lines)
- **Purpose**: Top-level studio wrapper. Manages selected color/view/size, toolbar, canvas, confirm-to-cart flow.
- **Key flow**: `handleConfirmDesign()` (line 173–207) → exports canvas PNGs, serializes design, dispatches `addItem`, shows toast, opens cart.
- **Backend relevance**: On confirm, design data (JSON + PNGs) should POST to server.

### `features/studio/components/StudioCanvas.jsx`
- **Purpose**: Konva Stage + Layers — background, design objects, UI overlays.
- **Backend relevance**: Client-only rendering.

### `features/studio/components/StudioDock.jsx`
- **Purpose**: Mobile floating toolbar at bottom of studio.
- **Backend relevance**: None.

### `features/studio/components/StudioPropertiesPanel.jsx`
- **Purpose**: Right-side panel for editing selected object properties (font, color, size, etc.).
- **Backend relevance**: None.

### `features/studio/components/ImageUploadButton.jsx`
- **Purpose**: Cloudinary upload with data-URL fallback.
- **Backend relevance**: In production, images should go through backend → Supabase Storage.

---

## Legacy Design Studio (`features/design-studio/`)

### `features/design-studio/studioSlice.js`
- **Purpose**: Fabric.js-based studio state. Simpler than Konva version.
- **Status**: **LEGACY / UNUSED** — not connected to router.

### `features/design-studio/useStudio.js` (502 lines)
- **Purpose**: Fabric.js canvas hook with history, safe zone, background management.
- **Status**: **LEGACY / UNUSED**.

### `features/design-studio/ImageUploadButton.jsx`
- **Purpose**: Duplicate of studio version but for Fabric.js.
- **Status**: **LEGACY / UNUSED**.

### `features/design-studio/useUrduFonts.js`
- **Purpose**: Identical to `features/studio/useUrduFonts.js`.
- **Status**: **DUPLICATE**.

---

## Hooks

### `hooks/useCloudinary.js`
- **Purpose**: Uploads images to Cloudinary CDN. Returns `secure_url` or `null` (fallback to data URL).
- **Config**: Reads `VITE_CLOUDINARY_CLOUD_NAME` and `VITE_CLOUDINARY_UPLOAD_PRESET` from env.
- **Backend relevance**: Consider routing through backend for signed uploads and tracking.

### `hooks/useDebounce.js`
- **Purpose**: Standard debounce hook. Used implicitly (e.g. search filtering).
- **Backend relevance**: None.

### `hooks/useLocalStorage.js`
- **Purpose**: `useState` + `localStorage` sync.
- **Backend relevance**: None — utility hook.

### `hooks/useMediaQuery.js`
- **Purpose**: CSS media query listener hook.
- **Backend relevance**: None.

### `hooks/useScrollLock.js`
- **⚠ ANOMALY**: Filename says "ScrollLock" but exports `useScrolled()`.
- **Backend relevance**: None.

### `hooks/useScrolled.js`
- **Duplicate**: Identical to `useScrollLock.js`.
- **Backend relevance**: None.

### `hooks/useToast.js`
- **Purpose**: DOM-based toast notification system (creates elements dynamically).
- **Tones**: `default` (indigo), `success` (green), `error` (red).
- **Backend relevance**: None.

---

## Components

### `components/atoms/Spinner.jsx`
- **Purpose**: Loading spinner (CSS animated div).
- **Backend relevance**: None.

### `components/molecules/QuantityInput.jsx`
- **Purpose**: +/- quantity control component.
- **Backend relevance**: None.

### `components/organisms/AnnouncementBar.jsx`
- **Purpose**: Top banner with rotating messages.
- **Backend relevance**: Could be admin-configurable in future.

### `components/organisms/SiteHeader.jsx`
- **Purpose**: Main navigation with cart count badge, auth-aware links.
- **Backend relevance**: Reads auth state for conditional rendering.

### `components/organisms/SiteFooter.jsx`
- **Purpose**: Site footer with navigation links.
- **Backend relevance**: None.

### `components/organisms/FilterBar.jsx`
- **Purpose**: Product filtering UI (category, sort, search).
- **Backend relevance**: Filter params will need to be passed to API query params.

### `components/organisms/ProductCard.jsx`
- **Purpose**: Product card rendering for collection grid.
- **Backend relevance**: Consumes product data shape.

### `components/organisms/UspStrip.jsx`
- **Purpose**: USP (unique selling proposition) strip below header.
- **Backend relevance**: Could be admin-configurable.

---

## Pages

### Auth Pages
| File | Lines | Backend calls |
|------|-------|---------------|
| `LoginPage.jsx` | 200 | `dispatch(loginUser(data))` |
| `SignupPage.jsx` | 319 | `dispatch(signupUser(data))` |
| `ForgotPasswordPage.jsx` | 80 | **NONE** — `e.preventDefault()` only |

### Storefront Pages
| File | Lines | Backend calls |
|------|-------|---------------|
| `HomePage.jsx` | 324 | Imports `PRODUCTS_MOCK` directly |
| `CollectionPage.jsx` | 44 | `useGetProductsQuery({category, sort, search})` |
| `ProductDetailPage.jsx` | 292 | `useGetProductBySlugQuery({slug})`, `dispatch(addItem(...))` |
| `CartPage.jsx` | 151 | Cart slice only (client-side) |
| `CheckoutPage.jsx` | 406 | `useCreateOrderMutation()` |
| `AccountPage.jsx` | 274 | `getOrders()` (direct API call, not RTK Query) |

### Studio Pages
| File | Lines | Backend calls |
|------|-------|---------------|
| `DesignStudioPage.jsx` | 42 | `useGetProductByIdQuery()`, `useGetProductsQuery()` |

### Admin Pages
| File | Lines | Backend calls |
|------|-------|---------------|
| `AdminDashboardPage.jsx` | 78 | `useGetOrdersQuery()` |
| `AdminOrdersPage.jsx` | 104 | `getOrders()`, `updateOrderStatus()` (direct API) |
| `AdminOrderDetails.jsx` | 52 | `useGetOrdersQuery()` |
| `OrderTable.jsx` | 118 | None — presentational |

---

## Utilities

### `utils/cn.js`
- **Purpose**: `clsx()` + `twMerge()` utility for conditional Tailwind classes.
- **Backend relevance**: None.

### `utils/currency.js`
- **Purpose**: `formatPKR(amount, compact?)` — formats number as "Rs. X,XXX".
- **Backend relevance**: Currency formatting should remain client-side; server returns raw numbers.

### `utils/validators.js`
- **Purpose**: Zod schemas for login, signup, and checkout forms.
- **Backend relevance**: Server should mirror these validations. Consider sharing schema definitions.

---

## Data

### `data/products.mock.js`
- **Purpose**: Hardcoded array of 8 products with full color/view/printArea data.
- **Backend relevance**: **REPLACE ENTIRELY** — this data moves to the products table in Supabase.

---

## Layouts

### `layouts/MainLayout.jsx`
- **Purpose**: Storefront shell — AnnouncementBar, SiteHeader, UspStrip, Outlet, SiteFooter, CartDrawer.
- **Backend relevance**: None.

### `layouts/AdminLayout.jsx`
- **Purpose**: Admin shell — sidebar with nav links, Outlet, sign-out handler.
- **Nav items**: Dashboard, Orders, Products, Designs, Customers, Settings.
- **Backend relevance**: Admin layout dispatches `logout()` on sign-out. Nav routes define future admin feature scope.
