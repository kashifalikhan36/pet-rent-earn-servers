# Pet Rent & Earn API Documentation

**Base URL:** `https://api.cvflow.tech`

This document provides a complete reference for all API endpoints available in the Pet Rent & Earn platform.

---

## 🔐 Authentication Endpoints (`/api/auth`)

### 1. Register User
**POST** `/api/auth/register`
Creates a new user account in the system.

```typescript
const registerUser = async (userData: {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}) => {
  const response = await axios.post('https://api.cvflow.tech/api/auth/register', userData);
  return response.data;
};
```

**Response (201):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_verified": false,
    "is_active": true,
    "role": "user"
  }
}
```

### 2. Login User
**POST** `/api/auth/login`
Authenticates a user with email and password (JSON or form-data supported).

```typescript
const loginUser = async (credentials: { email: string; password: string }) => {
  // JSON format supported
  const { data } = await axios.post('https://api.cvflow.tech/api/auth/login', credentials);
  return data;
};
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { "id": "...", "email": "...", "full_name": "..." }
}
```

### 3. Google OAuth Authentication ⭐ UPDATED

#### 3a. Get Google Auth URL
**GET** `/api/auth/google`
Get the Google OAuth authorization URL to redirect users for authentication.

```typescript
const getGoogleAuthUrl = async () => {
  const response = await axios.get('https://api.cvflow.tech/api/auth/google');
  window.location.href = response.data.auth_url;
  return response.data;
};
```

**Response (200):**
```json
{ "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=..." }
```

#### 3b. Google Login (API Response) ⭐ NEW
**POST** `/api/auth/google/login`
Returns JWT token directly (no redirect). Use this for API clients.

```typescript
const googleLogin = async (authCode: string) => {
  const { data } = await axios.post('https://api.cvflow.tech/api/auth/google/login', { code: authCode });
  localStorage.setItem('authToken', data.access_token);
  return data;
};
```

#### 3c. Google Callback (Redirect Flow)
**GET** `/api/auth/google/callback?code=...`
Handles the redirect from Google OAuth (for web applications). Automatically redirects to frontend with token.

#### 3d. Get Google User Info ⭐ NEW
**GET** `/api/auth/google/user-info?access_token=...`
Get user information from Google access token for verification purposes.

```typescript
const getGoogleUserInfo = async (googleAccessToken: string) => {
  const { data } = await axios.get(`https://api.cvflow.tech/api/auth/google/user-info?access_token=${googleAccessToken}`);
  return data;
};
```

### 4. Logout User
**POST** `/api/auth/logout`
Logs out the current authenticated user (client-side only for JWT).

```typescript
const logoutUser = async () => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post('https://api.cvflow.tech/api/auth/logout', {}, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 5. Get Current User
**GET** `/api/auth/me`
Retrieves information about the currently authenticated user.

```typescript
const getCurrentUser = async () => {
  const token = localStorage.getItem('authToken');
  const { data } = await axios.get('https://api.cvflow.tech/api/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return data;
};
```

### 6. Change Password
**POST** `/api/auth/change-password`
Changes the password for the authenticated user.

```typescript
const changePassword = async (currentPassword: string, newPassword: string) => {
  const token = localStorage.getItem('authToken');
  const { data } = await axios.post('https://api.cvflow.tech/api/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  }, { headers: { 'Authorization': `Bearer ${token}` } });
  return data; // { success: true }
};
```

### 7. Request Password Reset ⭐ UPDATED
**POST** `/api/auth/forgot-password`
Sends a password reset email to the user.

```typescript
const requestPasswordReset = async (email: string) => {
  const { data } = await axios.post('https://api.cvflow.tech/api/auth/forgot-password', { email });
  return data;
};
```

### 8. Reset Password ⭐ UPDATED
**POST** `/api/auth/reset-password`
Confirms password reset using the token from email.

```typescript
const resetPassword = async (token: string, newPassword: string) => {
  const { data } = await axios.post('https://api.cvflow.tech/api/auth/reset-password', { token, new_password: newPassword });
  return data;
};
```

### 9. Verify Reset Token ⭐ NEW
**GET** `/api/auth/verify-reset-token/{token}`
Verify if a reset token is valid.

### 10. Refresh Token ⭐ NEW
**POST** `/api/auth/refresh-token`
Refreshes JWT token for the authenticated user.

---

## 👤 User Management (`/api/users`)

Note: Some endpoints below have newer counterparts under Profile & Settings. Legacy routes remain for backward compatibility and are marked accordingly.

### 1. Get User Profile
**GET** `/api/users/profile`
Retrieves the current user's profile information. (Legacy; prefer GET /api/users/me)

```typescript
const getUserProfile = async () => {
  const token = localStorage.getItem('authToken');
  const { data } = await axios.get('https://api.cvflow.tech/api/users/profile', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return data;
};
```

### 2. Update User Profile
**PUT** `/api/users/profile`
Updates the current user's profile information. (Legacy; prefer PATCH /api/users/me)

```typescript
const updateUserProfile = async (profileData: Record<string, any>) => {
  const token = localStorage.getItem('authToken');
  const { data } = await axios.put('https://api.cvflow.tech/api/users/profile', profileData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return data;
};
```

### 3. Upload Avatar
- Legacy: **POST** `/api/users/upload-avatar`
- New: see Profile & Settings → `PUT /api/users/me/avatar`

```typescript
const uploadAvatarLegacy = async (file: File) => {
  const token = localStorage.getItem('authToken');
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await axios.post('https://api.cvflow.tech/api/users/upload-avatar', formData, {
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'multipart/form-data' }
  });
  return data;
};
```

### 4. Get Dashboard Analytics ⭐ UPDATED PATH
**GET** `/api/users/dashboard-analytics`
Detailed analytics for the user's dashboard.

### 5. Verification Status
**GET** `/api/users/verification-status`
Returns KYC/verification status for the current user.

### 6. Wallet
- Balance: **GET** `/api/users/wallet/balance`
- Update (testing/admin): **PUT** `/api/users/wallet`
- Detailed: **GET** `/api/users/wallet/detailed`

### 7. Detailed Profiles
- Own detailed profile: **GET** `/api/users/profile/detailed`
- Public detailed profile: **GET** `/api/users/{user_id}/profile`

### 8. Earnings & Payouts
- Earnings breakdown: **GET** `/api/users/earnings?months=12`
- Request payout: **POST** `/api/users/payout`
- List payouts: **GET** `/api/users/payouts`

### 9. Owner Analytics
- Overview: **GET** `/api/users/owner-analytics`
- Reviews aggregation: **GET** `/api/users/reviews-aggregation`
- Performance metrics: **GET** `/api/users/performance-metrics`

---

## 👤 Profile & Settings (under /api)

Note: Email-change endpoints have been removed. Do not call request-email-change or confirm-email-change.

- Profile
  - GET /api/users/me → MeProfileOut
  - PATCH /api/users/me → { success: true }
  - PUT /api/users/me/avatar → { avatar_url }
  - DELETE /api/users/me/avatar → { success: true }
  - GET /api/users/{id} (public) → PublicUserOut (respects privacy)

- Username & availability
  - GET /api/users/availability?username=foo → { available: boolean, suggestions?: string[] }

- Security & sessions
  - POST /api/auth/change-password → { success: true }
  - GET /api/auth/sessions → SessionOut[]
  - DELETE /api/auth/sessions → { success: true } (delete all)
  - DELETE /api/auth/sessions/{id} → { success: true }

- Notifications V2
  - GET /api/notifications/feed?page=1&per_page=20&unread_only=false → { items: NotificationFeedItem[], next_page?: number }
  - POST /api/notifications/read { ids?: string[] } → { message, count } (omit ids → all read)
  - GET /api/notifications/settings/v2 → NotificationSettingsV2
  - PATCH /api/notifications/settings → NotificationSettingsV2 (nested partial update)
  - Legacy retained: GET/PUT /api/notifications/settings (flat)

- Privacy & messaging
  - GET /api/users/me/privacy → PrivacySettings
  - PATCH /api/users/me/privacy → { success: true }
  - Blocks: GET /api/users/me/blocks → BlockedUserOut[]; POST /api/users/me/blocks { user_id } → { success: true }; DELETE /api/users/me/blocks/{user_id} → { success: true }

- Addresses (current user)
  - GET /api/users/me/addresses → AddressOut[]
  - POST /api/users/me/addresses → { id }
  - PATCH /api/users/me/addresses/{addr_id} → { success: true }
  - DELETE /api/users/me/addresses/{addr_id} → { success: true }
  - Rule: Only one default address at a time.

- Account lifecycle
  - POST /api/users/me/export → { success: true }
  - DELETE /api/users/me → { success: true } (password required if user has password)

Quick TS examples:

```typescript
// Me
const me = async () => axios.get('/api/users/me', auth()).then(r => r.data);
const updateMe = async (patch: any) => axios.patch('/api/users/me', patch, auth()).then(r => r.data);

// Availability
const checkUsername = (u: string) => axios.get('/api/users/availability', { params: { username: u } }).then(r => r.data);

// Sessions
const sessions = () => axios.get('/api/auth/sessions', auth()).then(r => r.data);
const revokeSession = (id: string) => axios.delete(`/api/auth/sessions/${id}`, auth());
```

---

## 💬 Chat/Conversations (`/api/conversations`)

### 1. Create Conversation
**POST** `/api/conversations`
Starts a new conversation with another user.

```typescript
const createConversation = async (recipientId: string, petId?: string, initialMessage?: string) => {
  const token = localStorage.getItem('authToken');
  const { data } = await axios.post('https://api.cvflow.tech/api/conversations', { recipient_id: recipientId, pet_id: petId, initial_message: initialMessage }, { headers: { 'Authorization': `Bearer ${token}` } });
  return data;
};
```

### 2. Get User Conversations
**GET** `/api/conversations`
Retrieves all conversations for the current user.

```typescript
const getUserConversations = async (archived = false, page = 1) => axios.get('/api/conversations', { params: { archived, page }, ...auth()}).then(r => r.data);
```

### 3. Get Conversation
**GET** `/api/conversations/{conversation_id}`
Gets a conversation with messages.

### 4. Send Message (Unified) ⭐ NEW
**POST** `/api/conversations/{conversation_id}/send`
Text, images, or both in one endpoint.

```typescript
const sendMessage = async (id: string, content?: string, images?: File[]) => {
  const fd = new FormData();
  if (content) fd.append('content', content);
  images?.forEach(f => fd.append('images', f));
  return axios.post(`/api/conversations/${id}/send`, fd, { headers: { ...auth().headers, 'Content-Type': 'multipart/form-data' } }).then(r => r.data);
};
```

### 5. Mark Conversation Read ⭐ NEW
**PUT** `/api/conversations/{conversation_id}/read`
Marks all messages as read.

### 6. Delete Message ⭐ NEW
**DELETE** `/api/conversations/{conversation_id}/messages/{message_id}`
Deletes a message (sender only).

### 7. Archive/Unarchive Conversation ⭐ NEW
**PUT** `/api/conversations/{conversation_id}/archive`
Body: `{ "archive": true | false }`.

### 8. Offers
- Create: **POST** `/api/conversations/{conversation_id}/offers`
- List: **GET** `/api/conversations/{conversation_id}/offers`
- Get one: **GET** `/api/conversations/{conversation_id}/offers/{offer_id}`
- Respond: **POST** `/api/conversations/{conversation_id}/offers/{offer_id}/respond`

Legacy (deprecated):
- `POST /api/conversations/{id}/messages` (text-only)
- `POST /api/conversations/{id}/images` (images-only)

---

## 🔔 Notifications (`/api/notifications`)

### V2 (recommended)
- Feed: **GET** `/api/notifications/feed?page=1&per_page=20&unread_only=false` → `{ items: NotificationFeedItem[], next_page?: number }`
- Mark read: **POST** `/api/notifications/read` body `{ ids?: string[] }` (omitting ids marks all)
- Get settings: **GET** `/api/notifications/settings/v2`
- Update settings (nested partial): **PATCH** `/api/notifications/settings`

```typescript
const getFeed = (p=1,u=false)=>axios.get('/api/notifications/feed',{params:{page:p,unread_only:u},...auth()}).then(r=>r.data);
const readSome = (ids?: string[])=>axios.post('/api/notifications/read',{ids},auth()).then(r=>r.data);
const getNotifSettings = ()=>axios.get('/api/notifications/settings/v2',auth()).then(r=>r.data);
const patchNotifSettings = (patch:any)=>axios.patch('/api/notifications/settings',patch,auth()).then(r=>r.data);
```

### Legacy
- List all: **GET** `/api/notifications`
- Unread: **GET** `/api/notifications/unread`
- Unread count: **GET** `/api/notifications/count`
- Mark one read: **PUT** `/api/notifications/{notification_id}/read`
- Mark all read: **PUT** `/api/notifications/read-all`
- Settings (flat): **GET/PUT** `/api/notifications/settings`

---

## 🐕 Pet Management (`/api/pets`)

### 1. Get All Pets
**GET** `/api/pets`
Retrieves a list of all active pet listings with optional filters.

```typescript
const getAllPets = async (filters?: {
  species?: string;
  breed?: string;
  city?: string;
  price_min?: number;
  price_max?: number;
  page?: number;
  per_page?: number;
}) => {
  const response = await axios.get('https://api.cvflow.tech/api/pets', { params: filters });
  return response.data;
};
```

### 2. Search Pets
**GET** `/api/pets/search`
Advanced search for pet listings with location and text search.

```typescript
const searchPets = async (searchParams: {
  q?: string;
  species?: string;
  latitude?: number;
  longitude?: number;
  radius?: number;
  page?: number;
}) => {
  const response = await axios.get('https://api.cvflow.tech/api/pets/search', { params: searchParams });
  return response.data;
};
```

### 3. Get Featured Pets
**GET** `/api/pets/featured`
Retrieves featured pet listings for homepage display.

```typescript
const getFeaturedPets = async (limit: number = 10) => {
  const response = await axios.get(`https://api.cvflow.tech/api/pets/featured?limit=${limit}`);
  return response.data;
};
```

### 4. Get Nearby Pets
**GET** `/api/pets/nearby`
Finds pets near a specific location using coordinates.

```typescript
const getNearbyPets = async (latitude: number, longitude: number, radius: number = 10) => {
  const response = await axios.get('https://api.cvflow.tech/api/pets/nearby', {
    params: { latitude, longitude, radius }
  });
  return response.data;
};
```

### 5. Create Pet Listing
**POST** `/api/pets`
Creates a new pet listing.

```typescript
const createPetListing = async (petData: {
  name: string;
  type: string;
  breed: string;
  age: number;
  description: string;
  price?: number;
  dailyRate?: number;
  location: object;
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post('https://api.cvflow.tech/api/pets', petData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 6. Get Pet by ID
**GET** `/api/pets/{pet_id}`
Retrieves detailed information about a specific pet.

```typescript
const getPetById = async (petId: string) => {
  const response = await axios.get(`https://api.cvflow.tech/api/pets/${petId}`);
  return response.data;
};
```

### 7. Update Pet Listing
**PUT** `/api/pets/{pet_id}`
Updates an existing pet listing (owner only).

```typescript
const updatePetListing = async (petId: string, updateData: object) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.put(`https://api.cvflow.tech/api/pets/${petId}`, updateData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 8. Delete Pet Listing
**DELETE** `/api/pets/{pet_id}`
Deletes a pet listing (owner only).

```typescript
const deletePetListing = async (petId: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.delete(`https://api.cvflow.tech/api/pets/${petId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 9. Upload Pet Photos
**POST** `/api/pets/{pet_id}/photos`
Uploads photos for a pet listing.

```typescript
const uploadPetPhotos = async (petId: string, file: File, caption?: string, isPrimary: boolean = false) => {
  const token = localStorage.getItem('authToken');
  const formData = new FormData();
  formData.append('file', file);
  if (caption) formData.append('caption', caption);
  formData.append('is_primary', isPrimary.toString());
  
  const response = await axios.post(`https://api.cvflow.tech/api/pets/${petId}/photos`, formData, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};
```

### 10. Add to Favorites
**POST** `/api/pets/{pet_id}/favorite`
Adds a pet to user's favorites list.

```typescript
const addToFavorites = async (petId: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post(`https://api.cvflow.tech/api/pets/${petId}/favorite`, {}, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 11. Remove from Favorites
**DELETE** `/api/pets/{pet_id}/favorite`
Removes a pet from user's favorites list.

```typescript
const removeFromFavorites = async (petId: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.delete(`https://api.cvflow.tech/api/pets/${petId}/favorite`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

---

## 📅 Booking Management (`/api/bookings`)

### 1. Create Booking
**POST** `/api/bookings`
Creates a new booking for a pet rental.

```typescript
const createBooking = async (bookingData: {
  pet_id: string;
  start_date: string;
  end_date: string;
  total_amount: number;
  notes?: string;
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post('https://api.cvflow.tech/api/bookings', bookingData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 2. Get User Bookings
**GET** `/api/bookings/my-bookings`
Retrieves all bookings for the current user.

```typescript
const getUserBookings = async (status?: string, page: number = 1) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get('https://api.cvflow.tech/api/bookings/my-bookings', {
    params: { status, page },
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 3. Update Booking Status
**PUT** `/api/bookings/{booking_id}/status`
Updates the status of a booking (accept, reject, cancel).

```typescript
const updateBookingStatus = async (bookingId: string, status: string, notes?: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.put(`https://api.cvflow.tech/api/bookings/${bookingId}/status`, {
    status, notes
  }, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

---

## 🏥 Health Records (`/api/health-records`)

### 1. Create Health Record
**POST** `/api/health-records/by-pet/{pet_id}`
Creates a health record for a pet.

```typescript
const createHealthRecord = async (petId: string, recordData: {
  record_type: string;
  title: string;
  description: string;
  date: string;
  veterinarian?: string;
  reminder_date?: string;
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post(`https://api.cvflow.tech/api/health-records/by-pet/${petId}`, recordData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 2. Get Pet Health Records
**GET** `/api/health-records/by-pet/{pet_id}`
Gets all health records for a specific pet.

```typescript
const getPetHealthRecords = async (petId: string, recordType?: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get(`https://api.cvflow.tech/api/health-records/by-pet/${petId}`, {
    params: { record_type: recordType },
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 3. Upload Health Record Attachment
**POST** `/api/health-records/{record_id}/attachments`
Uploads documents/images for a health record.

```typescript
const uploadHealthRecordAttachment = async (recordId: string, file: File) => {
  const token = localStorage.getItem('authToken');
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await axios.post(`https://api.cvflow.tech/api/health-records/${recordId}/attachments`, formData, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};
```

---

## 📋 Care Instructions (`/api/care-instructions`)

### 1. Create Care Instructions
**POST** `/api/care-instructions/pets/{pet_id}`
Creates detailed care instructions for a pet.

```typescript
const createCareInstructions = async (petId: string, instructionsData: {
  feeding: object;
  exercise: object;
  medical: object;
  emergency_contacts: object[];
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post(`https://api.cvflow.tech/api/care-instructions/pets/${petId}`, instructionsData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 2. Get Care Instructions
**GET** `/api/care-instructions/pets/{pet_id}`
Gets care instructions for a pet.

```typescript
const getCareInstructions = async (petId: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get(`https://api.cvflow.tech/api/care-instructions/pets/${petId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

---

## 🚩 Reports (`/api/reports`)

Report inappropriate content and manage reports.

- Report a user
  - POST `/api/reports/users/{user_id}` body: `{ reason, details?, evidence_urls? }`
- Report a pet
  - POST `/api/reports/pets/{pet_id}` body: `{ reason, details?, evidence_urls? }`
- Report a review
  - POST `/api/reports/reviews/{review_id}` body: `{ reason, details?, evidence_urls? }`
- Report a message
  - POST `/api/reports/messages/{message_id}` body: `{ reason, details?, evidence_urls? }`
- Upload evidence images
  - POST `/api/reports/evidence` multipart: `files[]` → `{ evidence_urls: string[] }`
- My reports
  - GET `/api/reports/my-reports?page=1&per_page=20`
- Get one
  - GET `/api/reports/{report_id}`
- Delete
  - DELETE `/api/reports/{report_id}`

Admin only:
- List all
  - GET `/api/reports?status=pending|reviewed|resolved&entity_type=user|pet|review|message&page=1&per_page=20`
- Update status
  - PUT `/api/reports/{report_id}/status` body: `{ status, admin_notes? }`

TypeScript examples:

```typescript
const reportUser = (userId: string, payload: { reason: string; details?: string; evidence_urls?: string[] }) =>
  axios.post(`/api/reports/users/${userId}`, payload, auth()).then(r => r.data);

const uploadReportEvidence = (files: File[]) => {
  const fd = new FormData();
  files.forEach(f => fd.append('files', f));
  return axios.post('/api/reports/evidence', fd, { headers: { ...auth().headers, 'Content-Type': 'multipart/form-data' } }).then(r => r.data);
};
```

---

## 💰 Transactions (`/api/transactions`)

### 1. Get User Transactions
**GET** `/api/transactions`
Retrieves transaction history for the current user.

```typescript
const getUserTransactions = async (type?: 'earning' | 'spending', page: number = 1) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get('https://api.cvflow.tech/api/transactions', {
    params: { type, page },
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

---

## 🏥 System Endpoints

### Health Check
**GET** `/health`
Checks if the API server is running and database is connected.

```typescript
const healthCheck = async () => {
  const response = await axios.get('https://api.cvflow.tech/health');
  return response.data;
};
```

**Response (200):**
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T12:00:00Z",
  "service": "Pet Rent & Earn API",
  "database": "connected",
  "version": "1.0.0"
}
```

### API Information
**GET** `/api`
Gets information about available API endpoints.

```typescript
const getApiInfo = async () => {
  const response = await axios.get('https://api.cvflow.tech/api');
  return response.data;
};
```

---

## Common Response Formats

### Success Response
```json
{
  "data": {},
  "message": "Operation successful",
  "status": "success"
}
```

### Error Response
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Validation Error Response
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Authentication

Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```typescript
headers: { 'Authorization': `Bearer ${token}` }
```

Store the token after successful login/registration and include it in subsequent requests.

---

## 🤖 AI Endpoints (`/api/ai`)

At this time, there are no AI endpoints implemented in this repository.

- If/when AI features are added, they will be under `/api/ai`.
- Once available, this section should enumerate each endpoint (method + path), required params, and example responses.