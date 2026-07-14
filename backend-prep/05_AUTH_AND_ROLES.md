# 05 — Auth & Roles

> Documents the current authentication and authorization implementation,
> what is mocked, and what the backend must provide.

---

## 1. Current Auth Implementation

### 1.1 Token Mechanism

**Source**: `api/auth.api.js:25`

The current "JWT" is a **base64-encoded JSON string** containing user profile data:

```js
// auth.api.js:25
const token = btoa(JSON.stringify({
  id: user.id,
  email: user.email,
  firstName: user.firstName,
  lastName: user.lastName,
  role: user.role,
}))
```

- Stored at: `localStorage['frill_token']` (`auth.api.js:5`)
- Decoded in: `getCurrentUser()` → `JSON.parse(atob(token))` (`auth.api.js:42–48`)
- **No signature, no expiry, no refresh mechanism**
- Anyone can forge a token by base64-encoding arbitrary JSON

### 1.2 Password Storage

**Source**: `api/auth.api.js:17`

Passwords are stored in **plaintext** in the `frill_users` localStorage array:

```js
const newUser = { ...data, id: crypto.randomUUID(), role: 'customer', createdAt: new Date().toISOString() }
```

The password field from the signup form is included as-is in the stored user object.

### 1.3 Login Verification

**Source**: `api/auth.api.js:40–52`

Login scans the users array for matching email and compares password as plaintext string equality:

```js
const user = users.find(u => u.email === email && u.password === password)
```

---

## 2. Roles

### 2.1 Role Values

**Source**: `api/auth.api.js:18`, `App.jsx:25`

Two roles exist:

| Role | Value | Assignment |
|------|-------|------------|
| Customer | `'customer'` | Default on signup (`auth.api.js:18`) |
| Admin | `'admin'` | Must be manually set (no admin creation flow exists) |

### 2.2 Role Enforcement

| Check Point | Location | How |
|-------------|----------|-----|
| Admin route guard | `App.jsx:18–28` (`AdminGuard`) | `selectUser(state)?.role !== 'admin'` → redirect to `/` |
| Post-login redirect | `LoginPage.jsx:35–36` | `role === 'admin' ? '/admin' : from` |
| Admin badge on account | `AccountPage.jsx:80–84` | Displays "👑 Admin" badge if `user.role === 'admin'` |
| Admin layout sign-out | `AdminLayout.jsx:23–26` | Dispatches `logout()` and navigates to `/login` |

### 2.3 What Is NOT Enforced

- **API-level authorization**: No mock API call checks the caller's role. Any request to `getOrders()` returns ALL orders regardless of who is logged in.
- **Checkout authentication**: Checkout does not require login. Orders have no `userId` field.
- **Design ownership**: Saved designs have no `userId` field. All designs are visible to all users.
- **Admin creation**: There is no UI or API for creating admin accounts. To test admin features, one must manually set `role: 'admin'` in localStorage.

---

## 3. Auth State in Redux

**Source**: `features/auth/authSlice.js`

```ts
interface AuthState {
  user:    User | null     // Current user profile
  token:   string | null   // The base64 "JWT"
  loading: boolean         // Async thunk loading state
  error:   string | null   // Last auth error message
}
```

### Async Thunks

| Thunk | Trigger | Mock behavior |
|-------|---------|---------------|
| `loginUser({ email, password })` | `LoginPage.jsx:33` | Scans localStorage users, returns fake token |
| `signupUser({ firstName, lastName, email, phone, password })` | `SignupPage.jsx:38` | Appends to localStorage users, returns fake token |
| `loadSession()` | [INFERRED] Called on app init | Reads token from localStorage, decodes |

### Selectors

| Selector | Returns |
|----------|---------|
| `selectUser` | `state.auth.user` |
| `selectIsAuthenticated` | `!!state.auth.token` |
| `selectAuthLoading` | `state.auth.loading` |
| `selectAuthError` | `state.auth.error` |

---

## 4. Session Lifecycle

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│ App starts  │───→│ loadSession()│───→│ Token in LS? │
└─────────────┘    └──────────────┘    └──────┬───────┘
                                              │
                                   Yes ───────┤──────── No
                                   │                    │
                              ┌────┴─────┐        ┌────┴─────┐
                              │ Decode   │        │ user=null│
                              │ base64   │        │ token=null│
                              │ Set user │        └──────────┘
                              └──────────┘

┌──────────┐    ┌──────────────┐    ┌──────────────┐
│ Login    │───→│ loginUser()  │───→│ Set user +   │
│ form     │    │              │    │ token in     │
│ submit   │    │              │    │ Redux + LS   │
└──────────┘    └──────────────┘    └──────────────┘

┌──────────┐    ┌──────────────┐    ┌──────────────┐
│ Logout   │───→│ logout()     │───→│ Clear user + │
│ click    │    │ reducer      │    │ token from   │
│          │    │              │    │ Redux + LS   │
└──────────┘    └──────────────┘    └──────────────┘
```

---

## 5. Protected Routes

| Route Pattern | Guard | Behavior |
|---------------|-------|----------|
| `/admin/*` | `AdminGuard` (`App.jsx:18–28`) | Not authenticated → redirect `/login`; Not admin → redirect `/` |
| `/account` | **NONE** (soft guard) | `AccountPage.jsx:36–53` shows login prompt if `!user`, but doesn't redirect |
| `/checkout` | **NONE** | Fully accessible to anonymous users |
| `/studio/:productId` | **NONE** | Fully accessible; designs can be added to cart without auth |

---

## 6. Social Login Buttons

**Source**: `LoginPage.jsx:170–178`, `SignupPage.jsx:288–296`

Three social login buttons are rendered using generic icons (Globe, CircleUserRound, Sparkles). They:
- Have **no `onClick` handlers**
- Have **no OAuth integration**
- Are purely decorative placeholders

---

## 7. Backend Requirements Summary

### Must implement:

1. **Supabase Auth integration**: Replace all of `api/auth.api.js` with Supabase `signUp()`, `signInWithPassword()`, `signOut()`, `getSession()`.
2. **Real JWT tokens**: With proper signing, expiry, and refresh.
3. **Server-side role checking**: RLS policies on all tables. Admin endpoints must verify role server-side, not just client-side route guards.
4. **User-order association**: Orders must store `userId` when the user is authenticated.
5. **User-design association**: Designs must store `userId`.
6. **Password hashing**: Supabase Auth handles this automatically.

### Should implement:

7. **Password reset flow**: Email-based reset via Supabase Auth.
8. **Social OAuth**: Google, Facebook, etc. via Supabase Auth providers.
9. **Admin user creation**: Seed script or admin invite flow.
10. **Profile update endpoint**: For the "Edit Profile" button.

### Nice to have:

11. **Email verification**: Post-signup email confirmation.
12. **Session invalidation**: Force logout on password change.
13. **Rate limiting**: On auth endpoints to prevent brute force.
