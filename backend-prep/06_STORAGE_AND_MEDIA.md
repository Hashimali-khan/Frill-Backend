# 06 — Storage & Media

> Documents every media/file handling pathway in the frontend:
> what gets uploaded, where it goes, and what the backend must provide.

---

## 1. Current Media Flows

### 1.1 Product Images

**Source**: `data/products.mock.js`

| Aspect | Detail |
|--------|--------|
| Source | External URLs (Unsplash) hardcoded in mock data |
| Used by | `ProductCard.jsx`, `ProductDetailPage.jsx`, `StudioCanvas.jsx`, `HomePage.jsx` |
| Format | JPEG/WebP via Unsplash CDN |
| Storage | None — URLs are properties of product records |

**Backend requirement**: Product images should be served from Supabase Storage or a CDN. Admin should be able to upload product photos.

---

### 1.2 Design Studio — User Image Uploads

**Source**: `features/studio/components/ImageUploadButton.jsx`, `hooks/useCloudinary.js`

**Upload flow**:
```
User selects file (PNG/JPEG/WebP/SVG, max 10MB)
         │
         ▼
┌─────────────────┐    Success    ┌──────────────────┐
│ Cloudinary API  │─────────────→│ Returns HTTPS URL │
│ (if configured) │              │ from Cloudinary   │
└────────┬────────┘              │ CDN               │
         │ Fail / Not configured └──────────────────┘
         ▼
┌─────────────────┐
│ FileReader      │
│ readAsDataURL() │──→ Returns base64 data URL
└─────────────────┘
```

| Aspect | Detail |
|--------|--------|
| Entry point | `ImageUploadButton.jsx:17–50` |
| Cloudinary config | `VITE_CLOUDINARY_CLOUD_NAME`, `VITE_CLOUDINARY_UPLOAD_PRESET` (`.env:4–5`) |
| Cloudinary endpoint | `https://api.cloudinary.com/v1_1/${cloudName}/image/upload` |
| Upload preset | Unsigned preset (no server signature) |
| Timeout | 30s (`useCloudinary.js:31`) |
| Max file size | 10MB client-side check (`ImageUploadButton.jsx:22`) |
| Accepted types | `image/png, image/jpeg, image/webp, image/svg+xml` |
| Fallback | Data URL (base64 string) if Cloudinary not configured or fails |

**Current Cloudinary config in `.env`**:
```
VITE_CLOUDINARY_CLOUD_NAME=devz7t6qd
VITE_CLOUDINARY_UPLOAD_PRESET=frill_designs
```

**Backend requirement**: Replace direct Cloudinary upload with Supabase Storage upload via backend API. The frontend should POST the file to the backend, which stores it in Supabase Storage and returns a public URL.

---

### 1.3 Design Studio — Canvas Exports

**Source**: `features/studio/components/StudioShell.jsx:135–171`

When the user clicks "Confirm Design", the canvas is exported to two PNG images:

| Export | Method | Resolution | Purpose |
|--------|--------|------------|---------|
| `mockupUrl` | `stage.toDataURL({ pixelRatio: 1 })` | 1x (canvas size) | Preview image for cart/order display |
| `printUrl` | `stage.toDataURL({ pixelRatio: 3 })` | 3x (high-res) | Print-ready file for production |

**Current storage**: Both are stored as **base64 data URLs** directly in the cart item (`StudioShell.jsx:194–195`), which then flows into the order record.

**Size concern**: A single 800×600 canvas at 3x resolution generates a PNG that can be 2–5 MB as a data URL. Two images per cart item = 4–10 MB. With multiple items, this bloats localStorage significantly.

**CORS handling**: `StudioShell.jsx:156–170` catches `SecurityError` when canvas is tainted by cross-origin images (e.g., Cloudinary URLs without proper CORS). In that case, it returns `null` for both URLs but still allows the item to be added to cart.

**Backend requirement**: After canvas export, the frontend should upload both PNGs to the backend → Supabase Storage, and store the returned URLs instead of data URLs.

---

### 1.4 Design JSON Serialization

**Source**: `features/studio/studioUtils.js:serializeDesign()`

The design state is serialized to a JSON string containing all design objects and background info. This string is stored as `cartItem.designJson`.

| Aspect | Detail |
|--------|--------|
| Content | All design objects (text, shapes, images) + background metadata |
| Image refs | `ImageObject.src` may contain data URLs (large) or Cloudinary URLs |
| Typical size | 1–50 KB for text-only designs; up to several MB if images are data URLs |
| Used for | Cart persistence, order records, design re-loading |

**Backend requirement**: Design JSON should be stored in the database (JSONB column) or as a file in Supabase Storage. Image references within the JSON should be URLs, not data URLs.

---

### 1.5 Saved Designs

**Source**: `api/designs.api.js`

| Aspect | Detail |
|--------|--------|
| Storage key | `localStorage['frill_designs_v2']` |
| Fields stored | `id, name, designJson, productId, colorId, viewId, mockupUrl, createdAt, updatedAt` |
| `mockupUrl` | Currently a data URL |

**Backend requirement**: Saved designs should be stored in Supabase DB with `mockupUrl` and image references pointing to Supabase Storage URLs.

---

## 2. External Services

### 2.1 Cloudinary

| Aspect | Detail |
|--------|--------|
| Purpose | User-uploaded design images (logos, artwork) |
| Auth | Unsigned upload preset (no API secret on client) |
| Cloud name | `devz7t6qd` (from `.env`) |
| Preset | `frill_designs` (from `.env`) |
| Used in | `hooks/useCloudinary.js` |

**Decision needed**: Keep Cloudinary for CDN delivery, switch to Supabase Storage, or use both?

### 2.2 Google Fonts

| Aspect | Detail |
|--------|--------|
| Purpose | Urdu font loading for design studio |
| Fonts | `Noto Nastaliq Urdu`, `Noto Naskh Arabic` |
| Loaded via | Dynamic `<link>` injection + FontFace API (`features/studio/useUrduFonts.js`) |
| Used in | Studio text rendering |

**Backend requirement**: None — client-side font loading continues as-is.

### 2.3 Unsplash

| Aspect | Detail |
|--------|--------|
| Purpose | Product photography and background images |
| Used in | `data/products.mock.js`, `LoginPage.jsx:44`, `SignupPage.jsx:49`, `HomePage.jsx:93` |
| Format | Direct hotlinked URLs with query params |

**Backend requirement**: Replace with self-hosted product images in Supabase Storage. Auth page backgrounds can remain as external URLs or be bundled as static assets.

---

## 3. Environment Variables (Media-related)

**Source**: `.env`, `.env.example`

| Variable | Purpose | Current value |
|----------|---------|---------------|
| `VITE_CLOUDINARY_CLOUD_NAME` | Cloudinary cloud identifier | `devz7t6qd` |
| `VITE_CLOUDINARY_UPLOAD_PRESET` | Unsigned upload preset name | `frill_designs` |
| `VITE_JAZZCASH_MERCHANT_ID` | JazzCash payment integration | Not set (in `.env.example` only) |
| `VITE_EASYPAISA_STORE_ID` | Easypaisa payment integration | Not set (in `.env.example` only) |
| `VITE_API_URL` | Backend API base URL | `https://api.example.com` (placeholder) |

**Backend requirement**: Add `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` for Supabase client initialization.

---

## 4. Storage Buckets Needed (Supabase)

| Bucket | Content | Access | Max size |
|--------|---------|--------|----------|
| `product-images` | Product photography (admin uploads) | Public read | 5 MB/image |
| `design-uploads` | User-uploaded logos/artwork for studio | Authenticated read/write, public read | 10 MB/file |
| `design-exports` | Canvas mockup + print PNGs | Authenticated write, public read | 10 MB/file |
| `design-json` | Serialized design JSON files (if stored as files) | Authenticated read/write | 1 MB/file |

---

## 5. Media Migration Checklist

- [ ] Product images: Migrate from Unsplash URLs to Supabase Storage
- [ ] User uploads: Route through backend → Supabase Storage instead of direct Cloudinary
- [ ] Canvas exports: Upload PNGs to Supabase Storage, store URLs instead of data URLs
- [ ] Design JSON: Store in DB (JSONB) or as Supabase Storage files
- [ ] Replace data URL references in design JSON with CDN URLs
- [ ] Set up Supabase Storage RLS policies for each bucket
- [ ] Configure CORS on Supabase Storage for canvas rendering
- [ ] Update `.env` with Supabase credentials
