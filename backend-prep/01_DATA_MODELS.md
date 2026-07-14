# 01 — Data Models

> Extracted from actual Redux slices, mock data files, API helpers, and Zod schemas.
> Every field is cited to its source.
> `[MOCK]` = generated client-side; will need server-side generation in production.

---

## 1. User

**Source**: `api/auth.api.js:14–22` (signup shape), `api/auth.api.js:40–52` (login lookup), `utils/validators.js` (Zod schemas)

```ts
interface User {
  id:        string     // UUID v4, generated client-side (auth.api.js:16) [MOCK]
  firstName: string     // Required, min 2 chars (validators.js — signupSchema)
  lastName:  string     // Required, min 2 chars
  email:     string     // Required, valid email format
  phone:     string     // Required, 11 digits (regex: /^\d{11}$/ — validators.js)
  password:  string     // Required, min 6 chars (stored in plaintext!) [MOCK]
  role:      'customer' | 'admin'  // Default: 'customer' (auth.api.js:18)
  createdAt: string     // ISO 8601 timestamp (auth.api.js:19) [MOCK]
}
```

**Storage**: `localStorage['frill_users']` — JSON array of User objects (`auth.api.js:9`)

**Notes**:
- Password is stored in cleartext in the mock (`auth.api.js:17`). Backend must hash.
- Token is a base64-encoded JSON string `{ id, email, firstName, lastName, role }` stored at `localStorage['frill_token']` (`auth.api.js:25`). Not a real JWT.
- No `updatedAt`, `avatar`, or `address` fields exist yet, but `AccountPage.jsx:109` renders an "Addresses" tab (future feature).

---

## 2. Product

**Source**: `data/products.mock.js` (PRODUCTS_MOCK array — 8 products)

```ts
interface Product {
  id:           string     // e.g. "classic-hoodie" — serves as both ID and slug
  slug:         string     // Same as id in current mock data
  name:         string     // e.g. "Classic Custom Hoodie"
  vendor:       string     // e.g. "Frill Essentials"
  category:     string     // e.g. "hoodies", "tees", "jackets", "trousers"
  desc:         string     // Short description
  longDesc:     string     // Extended description for product detail page
  price:        number     // Price in PKR (integer, e.g. 2499)
  oldPrice?:    number     // Strikethrough price (optional)
  stars:        number     // Rating (e.g. 4.8)
  reviews:      number     // Review count (e.g. 124)
  customizable: boolean    // If true, "Design Your Own" button appears
  img:          string     // Primary image URL (Unsplash)
  imgs:         string[]   // [INFERRED] Alternative image URLs for galleries
  sizes:        string[]   // e.g. ["XS","S","M","L","XL","2XL","3XL"]
  colors:       Color[]    // Array of color variants (see below)
}

interface Color {
  id:     string     // e.g. "hoodie-black"
  name:   string     // e.g. "Midnight Black"
  hex:    string     // e.g. "#1a1a2e"
  views:  View[]     // Array of product photography angles
}

interface View {
  id:        string     // e.g. "hoodie-black-front"
  label:     string     // e.g. "Front", "Back", "Side"
  imageUrl:  string     // Product photo URL
  printArea: PrintArea  // Coordinates for design placement
}

interface PrintArea {
  x:      number   // Left offset in canvas pixels
  y:      number   // Top offset in canvas pixels
  width:  number   // Width in canvas pixels
  height: number   // Height in canvas pixels
}
```

**Storage**: Hardcoded in `data/products.mock.js`. No localStorage. RTK Query endpoints read directly from this array.

**Notes**:
- `productsApi.js:12–27` filters by `category` (exact match), sorts by `price-asc`/`price-desc`/`name-az`/`name-za`, and searches by name (case-insensitive `includes`).
- `getProductBySlug` and `getProductById` both scan the same `PRODUCTS_MOCK` array (`productsApi.js:29–44`).
- The `customizable` flag controls whether the "Design Your Own" button appears on `ProductDetailPage.jsx:257–265`.

---

## 3. Cart Item

**Source**: `features/cart/cartSlice.js:6–32`

```ts
interface CartItem {
  key:               string    // Composite: `${productId}-${colorId}-${viewId}-${size}-${designId || 'no-design'}`
  productId:         string
  name:              string    // Product name
  img:               string    // Product primary image URL
  price:             number    // Unit price in PKR
  quantity:          number    // Min 1 (enforced in updateQuantity: cartSlice.js:42)
  selectedSize:      string    // e.g. "M"
  selectedColor:     string    // Hex value e.g. "#1a1a2e"
  selectedColorName: string    // e.g. "Midnight Black"
  selectedViewLabel: string | null  // e.g. "Front" or null
  mockupUrl:         string | null  // Data URL or Cloudinary URL of mockup PNG
  printUrl:          string | null  // Data URL of print-ready PNG (3x resolution)
  designJson:        string | null  // Serialized design JSON string
  designId:          string | null  // e.g. "design-1720000000000"
}
```

**Storage**: `localStorage['persist:frill-cart']` via redux-persist (`store/index.js:11–15`)

**Notes**:
- `addItem` action (`cartSlice.js:11–37`) either increments quantity if the same `key` exists, or pushes a new item.
- `updateQuantity` removes the item if quantity drops to 0 (`cartSlice.js:42–43`).

---

## 4. Design (Studio)

**Source**: `features/studio/studioSlice.js`, `features/studio/studioUtils.js`

### 4.1 Design State (Redux)

```ts
interface StudioDesign {
  objects: DesignObject[]
  background: {
    imageUrl:  string | null   // Product photo URL
    color:     string | null   // Garment hex color
    viewId:    string | null   // Current view ID
    viewLabel: string | null   // e.g. "Front"
    printArea: PrintArea       // { x, y, width, height }
  }
}
```

### 4.2 Design Objects

```ts
type DesignObject = TextObject | ImageObject | ShapeObject | LineObject

interface BaseObject {
  id:       string      // nanoid generated (studioSlice.js)
  type:     'text' | 'image' | 'rect' | 'circle' | 'line'
  x:        number
  y:        number
  rotation: number
  scaleX:   number
  scaleY:   number
  opacity:  number
}

interface TextObject extends BaseObject {
  type:       'text'
  text:       string
  fontFamily: string
  fontSize:   number
  fill:       string      // Color hex
  align:      string      // 'left' | 'center' | 'right'
  bold:       boolean
  italic:     boolean
  underline:  boolean
  direction:  'ltr' | 'rtl'   // For Urdu text support
}

interface ImageObject extends BaseObject {
  type: 'image'
  src:  string     // Data URL or Cloudinary URL
  width:  number
  height: number
}

interface ShapeObject extends BaseObject {
  type: 'rect' | 'circle'
  fill:   string
  stroke: string
  strokeWidth: number
  width?:  number   // rect
  height?: number   // rect
  radius?: number   // circle
}

interface LineObject extends BaseObject {
  type:   'line'
  points: number[]     // [x1,y1, x2,y2, ...]
  stroke: string
  strokeWidth: number
}
```

### 4.3 Serialized Design (for cart / persistence)

`studioUtils.js:serializeDesign()` converts the Redux design state to a JSON string:

```ts
function serializeDesign(design: StudioDesign): string
// Returns JSON.stringify({ objects, background })
```

This string is stored as `cartItem.designJson` and eventually in `localStorage['frill_designs_v2']`.

---

## 5. Order

**Source**: `api/orders.api.js`, `pages/storefront/CheckoutPage.jsx:98–103`, `features/orders/ordersApi.js`

```ts
interface Order {
  id:            string     // `ORD-${Date.now()}` [MOCK] (orders.api.js:6)
  // Contact info (from checkout step 1)
  firstName:     string
  lastName:      string
  email:         string
  phone:         string
  // Delivery info (from checkout step 2)
  address:       string
  city:          string
  province:      string     // One of: Punjab, Sindh, KPK, Balochistan, Gilgit-Baltistan, AJK
  postalCode:    string
  // Payment info (from checkout step 3)
  paymentMethod: 'cod' | 'jazzcash' | 'easypaisa'
  walletNumber:  string | ''   // Required if paymentMethod is jazzcash or easypaisa
  // Cart snapshot
  items:         CartItem[]    // Full cart items array at time of order
  count:         number        // Total item count
  total:         number        // Total price in PKR
  // Metadata
  status:        string        // 'pending' | 'processing' | 'shipped' | 'delivered' [MOCK default: 'pending']
  createdAt:     string        // ISO 8601 timestamp [MOCK]
  customerId?:   string        // [NOT SET] — currently no user association
}
```

**Storage**: `localStorage['frill_orders']` — JSON array (`orders.api.js:1`)

**Notes**:
- `createOrder()` (`orders.api.js:3–13`) assigns ID, status='pending', createdAt, and prepends to array.
- `updateOrderStatus()` (`orders.api.js:21–27`) finds by ID and patches the `status` field.
- `getOrders()` returns the entire array — **no filtering by user ID** (`orders.api.js:15–18`).
- `AccountPage.jsx:26` comments: "For now, show all orders (in production, filter by user.id)".

---

## 6. Saved Design

**Source**: `api/designs.api.js`

```ts
interface SavedDesign {
  id:         string     // `design-${Date.now()}` [MOCK] (designs.api.js:5)
  name:       string     // User-provided or auto-generated
  designJson: string     // Serialized design (from studioUtils.serializeDesign)
  productId:  string     // Associated product ID
  colorId:    string     // Color variant ID
  viewId:     string     // View (angle) ID
  mockupUrl:  string | null  // Preview image data URL
  createdAt:  string     // ISO 8601 timestamp [MOCK]
  updatedAt:  string     // ISO 8601 timestamp [MOCK]
}
```

**Storage**: `localStorage['frill_designs_v2']` — JSON array (`designs.api.js:1`)

**Notes**:
- `saveDesign()` prepends; `deleteDesign()` filters by ID; `getDesigns()` returns all.
- No user association (no `userId` field) — all designs are visible to all users in the mock.

---

## 7. Zod Validation Schemas

**Source**: `utils/validators.js`

### 7.1 Auth Schemas

```js
// loginSchema (validators.js)
{ email: z.string().email(), password: z.string().min(6) }

// signupSchema (validators.js)
{ firstName: z.string().min(2), lastName: z.string().min(2),
  email: z.string().email(), phone: z.string().regex(/^\d{11}$/),
  password: z.string().min(6),
  confirmPassword: z.string() }  // .refine(match password)
```

### 7.2 Checkout Schemas

```js
// checkoutStep1Schema — Contact
{ firstName: z.string().min(2), lastName: z.string().min(2),
  email: z.string().email(), phone: z.string().regex(/^\d{11}$/) }

// checkoutStep2Schema — Delivery
{ address: z.string().min(5), city: z.string().min(2),
  province: z.string().min(1), postalCode: z.string().optional() }

// checkoutStep3Schema — Payment
{ paymentMethod: z.enum(['cod','jazzcash','easypaisa']),
  walletNumber: z.string().optional() }
```

---

## 8. Relationships Diagram

```
┌──────────┐       ┌──────────────┐
│  User    │       │   Product    │
│ (no FK   │       │              │
│  on orders│       │ ─┬─ Colors  │
│  yet)    │       │  └── Views   │
└──────────┘       │     └ PrintArea│
                   └───────┬──────┘
                           │ product.id
                    ┌──────┴──────┐
                    │  CartItem   │
                    │  (in-memory)│
                    └──────┬──────┘
                           │ items[]
                    ┌──────┴──────┐
                    │   Order     │
                    │ (localStorage)│
                    └──────┬──────┘
                           │ designJson
                    ┌──────┴──────┐
                    │ SavedDesign │
                    │ (localStorage)│
                    └─────────────┘
```

**Key missing FK**: Orders have no `userId` / `customerId` linkage. The data is entirely disconnected from the auth system.
