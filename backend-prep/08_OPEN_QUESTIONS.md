# 08 — Open Questions

> Decisions that must be made before backend implementation begins.
> Grouped by domain. Each question explains the frontend assumption.

---

## Authentication

### Q1: Which Supabase Auth flow will be used?

The frontend currently has email+password login and signup. Supabase supports multiple flows:

- **Email + Password** (current pattern) — straightforward replacement
- **Magic Link** (passwordless) — would eliminate the password field from signup
- **OAuth** (Google, Facebook, etc.) — social login buttons already exist in the UI but are non-functional

**Frontend assumption**: Email + password. The auth API functions (`auth.api.js`) return `{ user, token }`.
Ans: email+password and oauth as mentioned in ui 

---

### Q2: Should checkout require authentication?

Currently, checkout is fully anonymous. The form collects contact info independently. This means:
- Orders have no `userId`
- Users can't view past orders unless they manually find them on the account page (which shows ALL orders)

**Options**:
- A) Require login before checkout (simpler RLS, better tracking)
- B) Allow guest checkout, optionally link to account if logged in
- C) Allow guest checkout with email-based order lookup

ans:option a


---

### Q3: How should admin accounts be created?

No admin creation flow exists. The current mock requires manually editing localStorage.

**Options**:
- A) Seed script that creates admin users in Supabase Auth + profiles table
- B) Admin invite flow (existing admin sends invite email)
- C) First-user-is-admin pattern
- D) Manual Supabase dashboard creation

ans: first admin can be seed it should be super admin and can only mangae other admins and can assign a admin to super admin

---

## Products

### Q4: Should `id` and `slug` be separate fields?

In the current mock, `product.id === product.slug` (e.g., `"classic-hoodie"`). The frontend has two query endpoints:
- `getProductBySlug({slug})` — used by `ProductDetailPage` (URL routing)
- `getProductById({id})` — used by `DesignStudioPage`

**Options**:
- A) Use UUID for `id`, human-readable string for `slug` (recommended)
- B) Keep single field serving as both (current behavior)

ans:option a

---

### Q5: Who manages product data?

No admin product management UI exists (the route is a placeholder). Questions:
- Will products be managed via the admin panel UI?
- Will they be seeded from a script or imported from a spreadsheet?
- Should the product structure (colors, views, print areas) be admin-editable or developer-managed?

ans: yes products will be managable through admin ui and product structure can be editable inshort there should be minimal devolper interaction need after system delivery 
---

### Q6: How should print areas be defined?

Each product view has a `printArea: { x, y, width, height }` in the mock data. These coordinates are specific to the canvas dimensions and the product photo composition.

- Are these hand-tuned per photo? (current approach)
- Should there be an admin tool to visually define print areas?
- Should the design studio auto-calculate based on garment detection?
 ans:  Should there be an admin tool to visually define print area
---

## Orders

### Q7: What is the order status pipeline?

`AdminOrdersPage.jsx:7` defines: `['pending', 'processing', 'shipped', 'delivered']`

But there's a case mismatch with `OrderTable.jsx` (see Bug B1 in 07_GAPS_AND_INCONSISTENCIES.md).

**Questions**:
- Is this the final pipeline? Should there be additional states (e.g., `cancelled`, `refunded`, `on-hold`)?
- Should status transitions be validated server-side (e.g., can't go from `delivered` back to `pending`)?
- Should status changes trigger notifications (email, SMS)?
yes all of above 
---

### Q8: Should orders store cart items inline or reference products?

Currently, the entire cart item array (including product names, prices, images, design JSON, mockup data URLs) is stored verbatim in the order record.

**Options**:
- A) Store `order_items` as a separate table with `product_id` FK (normalized)
- B) Store the full snapshot as JSONB (denormalized, preserves historical prices)
- C) Hybrid: separate table but with snapshotted `price_at_order` and `name_at_order`
answer =We are going to use the Hybrid Snapshot Pattern. This gives us the best of both worlds.

We will create a dedicated order_items table in our Postgres database. When an order is placed, we will insert a row for each item in the cart.

We will store the product_id as a Foreign Key. This allows us to run clean, fast analytics queries joining orders to products.

We will also create specific snapshot columns on the order_items table: price_at_order and name_at_order. At the exact moment of checkout, FastAPI will copy the live price and name into these columns.

This freezes the financial reality in time forever, while keeping the data perfectly structured and queryable.

---

### Q9: How should order payments be handled?

The checkout collects `paymentMethod` ('cod', 'jazzcash', 'easypaisa') and optionally a `walletNumber`. `.env.example` includes `VITE_JAZZCASH_MERCHANT_ID` and `VITE_EASYPAISA_STORE_ID` but no payment integration code exists.

**Questions**:
- Is COD the only supported method at launch?
- Should JazzCash/Easypaisa integration happen before or after backend launch?
- Should payment verification happen server-side before order confirmation?
we will implement stripe but for deomo version we can switch it off and in future when we launch just have to active it ;
---

## Designs

### Q10: Should designs be saved to the server automatically or on-demand?

Currently, `designsApi` has a `saveDesign` mutation, but it's never called from any page. The design only persists when it's added to cart (as `designJson` in the cart item).

**Options**:
- A) Auto-save designs periodically (like Google Docs)
- B) Explicit "Save Design" button (the API exists but no UI calls it)
- C) Only persist through cart/order (current behavior

option B

---

### Q11: Should design JSON contain embedded images or references?

Currently, `ImageObject.src` in the design JSON can be either:
- A Cloudinary URL (if upload succeeded)
- A base64 data URL (if Cloudinary not configured or failed)

For database storage, data URLs are problematic (large, non-cacheable).

**Recommended**: All image references in design JSON should be URLs pointing to Supabase Storage objects.

answer =All image references in design JSON should be URLs pointing to Supabase Storage objects.

---

## Media

### Q12: Keep Cloudinary or move entirely to Supabase Storage?

Current state: Cloudinary is configured and working for design image uploads. Supabase Storage would be the natural choice for the Supabase-based backend.

**Options**:
- A) Move entirely to Supabase Storage (simpler, single platform)
- B) Keep Cloudinary for image transformations/CDN, use Supabase Storage for other files
- C) Use both with different purposes (Cloudinary for public CDN, Supabase for private storage)
option A: but we have to do something about image compression and decompression
---

### Q13: How should canvas exports be handled?

The `printUrl` (3x PNG) can be 2–5 MB. Options for production:
- A) Upload to Supabase Storage immediately on "Confirm Design"
- B) Re-generate server-side from design JSON when needed
- C) Generate on-demand when admin views order
answer: option b
---

## Architecture

### Q14: Should the frontend call Supabase directly or go through FastAPI?

Two common patterns:
- A) Frontend → FastAPI → Supabase (backend as API gateway)
- B) Frontend → Supabase (direct, with RLS) for auth/data, FastAPI for business logic only
- C) Hybrid: Supabase Auth direct, data through FastAPI

**Frontend assumption**: RTK Query's `baseQuery` will point to a single API URL (`VITE_API_URL`).
answer=option a
---

### Q15: Should RTK Query endpoints switch to `fetchBaseQuery` or use Supabase JS client?

Currently all RTK Query endpoints use `queryFn` (no `baseQuery`). When connecting to the backend:

**Options**:
- A) `fetchBaseQuery({ baseUrl: '/api' })` with `prepareHeaders` injecting the Supabase JWT (standard REST pattern)
- B) Use `@supabase/supabase-js` client within `queryFn` (couples frontend to Supabase)
- C) A) for custom endpoints, B) for Supabase-native operations (auth, storage)
answer: optio a
---

### Q16: What about real-time features?

Supabase supports real-time subscriptions (Postgres changes). Potential uses:
- Order status updates (admin and customer)
- New order notifications for admin
- Design auto-save

**Question**: Are real-time features in scope for the initial backend launch?
yes they are 
