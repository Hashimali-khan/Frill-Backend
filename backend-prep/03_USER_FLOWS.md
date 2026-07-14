# 03 — User Flows

> Step-by-step trace of every user-facing workflow in the frontend.
> Each step cites the source file and line numbers.
> `[MOCK]` marks where the flow currently terminates at localStorage.
> `[BACKEND]` marks where a real API call will be needed.

---

## Flow 1: User Signup

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | User visits `/signup` | `App.jsx:72` | — |
| 2 | Fills out: firstName, lastName, email, phone, password, confirmPassword | `SignupPage.jsx:91–233` | — |
| 3 | Checks "Terms" checkbox | `SignupPage.jsx:238–256` | — |
| 4 | Submits form → Zod validation via `signupSchema` | `SignupPage.jsx:27–29`, `validators.js` | — |
| 5 | `dispatch(signupUser(data))` → calls `api/auth.api.js:signup()` | `SignupPage.jsx:38`, `authSlice.js` | [BACKEND] POST `/auth/signup` |
| 6 | [MOCK] Checks if email exists in `frill_users`, appends new user, generates base64 "token" | `auth.api.js:9–30` | [BACKEND] Supabase Auth `signUp()` |
| 7 | On success: navigates to `/` | `SignupPage.jsx:41` | — |

---

## Flow 2: User Login

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | User visits `/login` | `App.jsx:71` | — |
| 2 | Fills out: email, password | `LoginPage.jsx:82–138` | — |
| 3 | Submits → Zod validation via `loginSchema` | `LoginPage.jsx:28–30` | — |
| 4 | `dispatch(loginUser(data))` → calls `auth.api.js:login()` | `LoginPage.jsx:33–34` | [BACKEND] POST `/auth/login` |
| 5 | [MOCK] Scans `frill_users` for matching email/password | `auth.api.js:40–52` | [BACKEND] Supabase Auth `signInWithPassword()` |
| 6 | On success: if `role === 'admin'` → navigate `/admin`; else → navigate to `from` (original page) or `/` | `LoginPage.jsx:35–37` | — |

---

## Flow 3: Session Restore

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | App mounts → `store/index.js` creates store | `main.jsx:5–9` | — |
| 2 | `authSlice` initial state has `user: null` | `authSlice.js` | — |
| 3 | [INFERRED] `loadSession` thunk should be dispatched on app init | `authSlice.js` | [BACKEND] GET `/auth/me` or Supabase `getSession()` |
| 4 | [MOCK] Reads `frill_token` from localStorage, base64-decodes | `auth.api.js:40–52` | [BACKEND] Validate JWT server-side |

**Note**: No explicit `loadSession` dispatch was found in `main.jsx` or `App.jsx`. The session restore mechanism may rely on PersistGate or manual dispatch elsewhere.

---

## Flow 4: Browse Products

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | User visits `/collections` | `App.jsx:62` | — |
| 2 | `CollectionPage` calls `useGetProductsQuery({category, sort, search})` | `CollectionPage.jsx:10–14` | [BACKEND] GET `/api/products?category=X&sort=Y&q=Z` |
| 3 | [MOCK] `productsApi` queryFn filters `PRODUCTS_MOCK` array | `productsApi.js:12–27` | [BACKEND] Supabase query |
| 4 | Products rendered in grid via `ProductCard` | `CollectionPage.jsx:35–38` | — |
| 5 | `FilterBar` provides category/sort/search controls, updates URL params | `FilterBar.jsx` | — |

---

## Flow 5: View Product Detail

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | User clicks ProductCard → navigates to `/products/:slug` | `ProductCard.jsx` (Link) | — |
| 2 | `ProductDetailPage` calls `useGetProductBySlugQuery({slug})` | `ProductDetailPage.jsx:18` | [BACKEND] GET `/api/products/:slug` |
| 3 | [MOCK] `productsApi` scans `PRODUCTS_MOCK` by slug | `productsApi.js:29–37` | [BACKEND] Supabase query |
| 4 | User selects color → updates `activeColor`, resets view to first of that color | `ProductDetailPage.jsx:189–192` | — |
| 5 | User selects view thumbnail → updates hero image | `ProductDetailPage.jsx:126–135` | — |
| 6 | User selects size | `ProductDetailPage.jsx:213–228` | — |
| 7 | User adjusts quantity via `QuantityInput` | `ProductDetailPage.jsx:242` | — |
| 8a | **Add to Cart** → `dispatch(addItem({product, quantity, selectedSize, selectedColor, selectedView}))` | `ProductDetailPage.jsx:83–98` | — (client-side) |
| 8b | **Design Your Own** → navigates to `/studio/:productId` with state `{selectedColorId, selectedViewId}` | `ProductDetailPage.jsx:101–108` | — |

---

## Flow 6: Design Studio

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | User arrives at `/studio/:productId` | `App.jsx:66` | — |
| 2 | `DesignStudioPage` loads product via `useGetProductByIdQuery({id})` | `DesignStudioPage.jsx:12–15` | [BACKEND] GET `/api/products/:id` |
| 3 | Renders `StudioShell` with product + initial color/view | `DesignStudioPage.jsx:33–39` | — |
| 4 | `StudioShell` dispatches `setProductContext()` and `setBackground()` | `StudioShell.jsx:95–114` | — |
| 5 | User interacts with tools: Add Text, Add Urdu, Upload Image, Add Shapes, Brush | `StudioShell.jsx:329–384` | — |
| 6 | Upload Image → Cloudinary API (optional) or data URL fallback | `ImageUploadButton.jsx`, `useCloudinary.js` | [BACKEND] Image upload to Supabase Storage |
| 7 | Each design mutation → Redux dispatches → `studioHistoryMiddleware` captures snapshot for undo/redo | `studioHistoryMiddleware.js` | — |
| 8 | User changes color/view → dispatches `setBackground()` with new product image | `StudioShell.jsx:416–450` | — |
| 9 | **Confirm Design** → `handleConfirmDesign()`: | `StudioShell.jsx:173–207` | — |
| 9a | Exports canvas → `mockupUrl` (1x PNG) + `printUrl` (3x PNG) | `StudioShell.jsx:135–171` | [BACKEND] Upload PNGs to Supabase Storage |
| 9b | `serializeDesign(design)` → JSON string | `studioUtils.js` | — |
| 9c | `dispatch(addItem({...product, mockupUrl, printUrl, designJson, designId}))` | `StudioShell.jsx:180–199` | — |
| 9d | Shows toast "Design added to cart!" + opens cart drawer | `StudioShell.jsx:202–203` | — |

---

## Flow 7: Cart Management

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | User views cart via `/cart` or CartDrawer (slide-over) | `CartPage.jsx`, `CartDrawer.jsx` | — |
| 2 | Sees item list with mockup images, sizes, colors, quantities, prices | `CartPage.jsx:61–114` | — |
| 3 | Adjust quantity → `dispatch(updateQuantity({key, quantity}))` | `CartPage.jsx:98–107` | — |
| 4 | Remove item → `dispatch(removeItem(key))` | `CartPage.jsx:87` | — |
| 5 | Click "Proceed to Checkout" → navigates to `/checkout` | `CartPage.jsx:134` | — |

---

## Flow 8: Checkout (3-step)

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | User lands on `/checkout` | `App.jsx:65` | — |
| 2 | **Empty cart guard**: If `items.length === 0`, shows empty state | `CheckoutPage.jsx:183–201` | — |
| 3 | **Step 1 — Contact**: firstName, lastName, email, phone | `CheckoutPage.jsx:230–244` | — |
| 4 | Validates via `checkoutStep1Schema` → advances to step 2 | `CheckoutPage.jsx:60–61, 87–96` | — |
| 5 | **Step 2 — Delivery**: address, city, postalCode, province (select from 6 provinces) | `CheckoutPage.jsx:247–270` | — |
| 6 | Validates via `checkoutStep2Schema` → advances to step 3 | Same flow | — |
| 7 | **Step 3 — Payment**: Radio select (JazzCash / Easypaisa / COD) | `CheckoutPage.jsx:273–298` | — |
| 8 | If JazzCash/Easypaisa → reveals wallet number input | `CheckoutPage.jsx:291–297` | — |
| 9 | Validates via `checkoutStep3Schema` → submit | Same flow | — |
| 10 | `createOrder(finalOrder).unwrap()` | `CheckoutPage.jsx:106–107` | [BACKEND] POST `/api/orders` |
| 11 | [MOCK] Creates order in localStorage with `ORD-${Date.now()}` ID | `orders.api.js:3–13` | [BACKEND] Insert into Supabase `orders` table |
| 12 | On success: `setSubmittedOrder(savedOrder)`, `dispatch(clearCart())` | `CheckoutPage.jsx:109–110` | — |
| 13 | On error: Still shows success but with the local order data | `CheckoutPage.jsx:113–117` | [BACKEND] Show actual error |
| 14 | Confirmation screen with order ID, contact info, payment method | `CheckoutPage.jsx:124–180` | — |

**⚠ No auth required**: Checkout is open to anonymous users. The order has no `userId`.

---

## Flow 9: Account Page

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | User visits `/account` | `App.jsx:64` | — |
| 2 | If not logged in → shows login prompt | `AccountPage.jsx:36–53` | — |
| 3 | **Profile tab**: Displays user data (name, email, phone, role) | `AccountPage.jsx:121–182` | [BACKEND] GET `/api/users/me` |
| 4 | "Edit Profile" button exists but has no handler | `AccountPage.jsx:179–181` | [BACKEND] PUT `/api/users/me` (future) |
| 5 | **Orders tab**: Calls `getOrders()` → loads ALL orders (no user filtering) | `AccountPage.jsx:22–33` | [BACKEND] GET `/api/orders?userId=X` |
| 6 | Renders order table with ID, date, items, total, status | `AccountPage.jsx:225–263` | — |
| 7 | "Addresses" and "Settings" tabs → button only, no content | `AccountPage.jsx:109–114` | [BACKEND] Future feature |

---

## Flow 10: Admin Dashboard

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | Admin visits `/admin` (guarded by AdminGuard) | `App.jsx:75–79` | — |
| 2 | KPI cards show hardcoded data (Revenue: 248500, Orders: 17, etc.) | `AdminDashboardPage.jsx:8–13` | [BACKEND] GET `/api/admin/stats` |
| 3 | Recent orders loaded via `useGetOrdersQuery()` | `AdminDashboardPage.jsx:26` | [BACKEND] GET `/api/orders?limit=5&sort=recent` |
| 4 | Renders `OrderTable` with `variant="dashboard"` (compact view) | `AdminDashboardPage.jsx:73` | — |
| 5 | "View All Orders" links to `/admin/orders` | `AdminDashboardPage.jsx:67–69` | — |

---

## Flow 11: Admin Order Management

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | Admin visits `/admin/orders` | `App.jsx:80` | — |
| 2 | Loads all orders via `getOrders()` (direct API call, not RTK Query) | `AdminOrdersPage.jsx:25–36` | [BACKEND] GET `/api/orders` |
| 3 | Filter tabs: All, Pending, Processing, Shipped, Delivered | `AdminOrdersPage.jsx:65–83` | — (client-side filter) |
| 4 | **Advance Status**: `advanceStatus(orderId)` → determines next status, calls `updateOrderStatus()` | `AdminOrdersPage.jsx:38–53` | [BACKEND] PATCH `/api/orders/:id/status` |
| 5 | [MOCK] Updates status in localStorage | `orders.api.js:21–27` | [BACKEND] Update in Supabase |
| 6 | **View Details**: Links to `/admin/orders/:orderId` | `OrderTable.jsx:100` | — |
| 7 | `AdminOrderDetails` finds order in RTK Query cache | `AdminOrderDetails.jsx:6–8` | [BACKEND] GET `/api/orders/:id` |
| 8 | Shows customer info, status, items list with mockup images | `AdminOrderDetails.jsx:18–48` | — |
| 9 | Checks for `item.designJson` to show "Custom design attached" badge | `AdminOrderDetails.jsx:40` | [BACKEND] Link to design view/download |

---

## Flow 12: Logout

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1a | From storefront: `SiteHeader` logout button → `dispatch(logout())` | `SiteHeader.jsx` | — |
| 1b | From admin: `AdminLayout` sign out → `dispatch(logout())` + navigate `/login` | `AdminLayout.jsx:23–26` | — |
| 2 | `logout` reducer → clears `frill_token` from localStorage, resets user/token state | `authSlice.js` | [BACKEND] Supabase `signOut()` |

---

## Flow 13: Cart Drawer (Slide-over)

| Step | Action | Source | Backend needed? |
|------|--------|--------|-----------------|
| 1 | Cart icon click in `SiteHeader` → `dispatch(openCart())` | `SiteHeader.jsx` | — |
| 2 | `CartDrawer` renders as slide-over panel | `CartDrawer.jsx` | — |
| 3 | Shows items, quantities, total | `CartDrawer.jsx` | — |
| 4 | Adjust/remove items → same cart dispatches | `CartDrawer.jsx` | — |
| 5 | "View Cart" → navigates to `/cart` | `CartDrawer.jsx` | — |
| 6 | "Checkout" → navigates to `/checkout` | `CartDrawer.jsx` | — |
| 7 | Close: backdrop click or X button → `dispatch(closeCart())` | `CartDrawer.jsx` | — |
