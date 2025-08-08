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
Authenticates a user with email and password.

```typescript
const loginUser = async (credentials: { email: string; password: string }) => {
  const formData = new FormData();
  formData.append('username', credentials.email);
  formData.append('password', credentials.password);
  
  const response = await axios.post('https://api.cvflow.tech/api/auth/login', formData);
  return response.data;
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

### 3. Google OAuth Login
**POST** `/api/auth/google`
Authenticates a user using Google OAuth ID token.

```typescript
const googleLogin = async (idToken: string) => {
  const response = await axios.post('https://api.cvflow.tech/api/auth/google', { id_token: idToken });
  return response.data;
};
```

### 4. Logout User
**POST** `/api/auth/logout`
Logs out the current authenticated user.

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
  const response = await axios.get('https://api.cvflow.tech/api/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 6. Change Password
**POST** `/api/auth/change-password`
Changes the password for the authenticated user.

```typescript
const changePassword = async (currentPassword: string, newPassword: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post('https://api.cvflow.tech/api/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  }, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 7. Request Password Reset
**POST** `/api/auth/password-reset`
Sends a password reset email to the user.

```typescript
const requestPasswordReset = async (email: string) => {
  const response = await axios.post('https://api.cvflow.tech/api/auth/password-reset', { email });
  return response.data;
};
```

### 8. Confirm Password Reset
**POST** `/api/auth/password-reset/confirm`
Confirms password reset using the token from email.

```typescript
const confirmPasswordReset = async (token: string, newPassword: string) => {
  const response = await axios.post('https://api.cvflow.tech/api/auth/password-reset/confirm', {
    token, new_password: newPassword
  });
  return response.data;
};
```

---

## 👤 User Management (`/api/users`)

### 1. Get User Profile
**GET** `/api/users/profile`
Retrieves the current user's profile information.

```typescript
const getUserProfile = async () => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get('https://api.cvflow.tech/api/users/profile', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 2. Update User Profile
**PUT** `/api/users/profile`
Updates the current user's profile information.

```typescript
const updateUserProfile = async (profileData: {
  full_name?: string;
  phone?: string;
  bio?: string;
  location?: object;
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.put('https://api.cvflow.tech/api/users/profile', profileData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 3. Upload Avatar
**POST** `/api/users/avatar`
Uploads a profile picture for the user.

```typescript
const uploadAvatar = async (file: File) => {
  const token = localStorage.getItem('authToken');
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await axios.post('https://api.cvflow.tech/api/users/avatar', formData, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};
```

### 4. Get User Dashboard Analytics
**GET** `/api/users/dashboard`
Retrieves analytics data for the user's dashboard.

```typescript
const getUserDashboard = async () => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get('https://api.cvflow.tech/api/users/dashboard', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

**Response (200):**
```json
{
  "total_pets": 5,
  "active_bookings": 2,
  "total_earnings": 1500.00,
  "recent_activity": [],
  "wallet_balance": 750.00
}
```

### 5. Submit Verification Documents
**POST** `/api/users/documents`
Submits identity verification documents.

```typescript
const submitDocuments = async (files: File[], documentType: string) => {
  const token = localStorage.getItem('authToken');
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('document_type', documentType);
  
  const response = await axios.post('https://api.cvflow.tech/api/users/documents', formData, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};
```

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

## 💬 Chat/Conversations (`/api/conversations`)

### 1. Create Conversation
**POST** `/api/conversations`
Starts a new conversation with another user.

```typescript
const createConversation = async (recipientId: string, petId?: string, initialMessage?: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post('https://api.cvflow.tech/api/conversations', {
    recipient_id: recipientId,
    pet_id: petId,
    initial_message: initialMessage
  }, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 2. Get User Conversations
**GET** `/api/conversations`
Retrieves all conversations for the current user.

```typescript
const getUserConversations = async (archived: boolean = false, page: number = 1) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get('https://api.cvflow.tech/api/conversations', {
    params: { archived, page },
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 3. Get Conversation Messages
**GET** `/api/conversations/{conversation_id}`
Retrieves a specific conversation with all messages.

```typescript
const getConversation = async (conversationId: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get(`https://api.cvflow.tech/api/conversations/${conversationId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 4. Send Message (Unified) ⭐ NEW
**POST** `/api/conversations/{conversation_id}/send`
Professional unified endpoint to send text, images, or both in a single request with smart auto-detection.

```typescript
// Send text message (message_type is auto-detected)
const sendTextMessage = async (conversationId: string, content: string) => {
  const token = localStorage.getItem('authToken');
  const formData = new FormData();
  formData.append('content', content);
  // message_type automatically detected as 'text'
  
  const response = await axios.post(`https://api.cvflow.tech/api/conversations/${conversationId}/send`, formData, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};

// Send images only (message_type is auto-detected)
const sendImages = async (conversationId: string, files: File[]) => {
  const token = localStorage.getItem('authToken');
  const formData = new FormData();
  // message_type automatically detected as 'image'
  files.forEach(file => formData.append('images', file));
  
  const response = await axios.post(`https://api.cvflow.tech/api/conversations/${conversationId}/send`, formData, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};

// Send text with images (message_type is auto-detected as 'mixed')
const sendMixedMessage = async (conversationId: string, content: string, files: File[]) => {
  const token = localStorage.getItem('authToken');
  const formData = new FormData();
  formData.append('content', content);
  // message_type automatically detected as 'mixed'
  files.forEach(file => formData.append('images', file));
  
  const response = await axios.post(`https://api.cvflow.tech/api/conversations/${conversationId}/send`, formData, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};
```

**Note**: The `message_type` parameter is optional - the API automatically detects the type based on content and images provided!

### 5. Send Message (Legacy)
**POST** `/api/conversations/{conversation_id}/messages` - DEPRECATED
Legacy endpoint for text messages only. Use the unified `/send` endpoint instead.

### 6. Send Images (Legacy)
**POST** `/api/conversations/{conversation_id}/images` - DEPRECATED
Legacy endpoint for images only. Use the unified `/send` endpoint instead.

### 7. Create Offer
**POST** `/api/conversations/{conversation_id}/offers`
Creates a rental offer within a conversation.

```typescript
const createOffer = async (conversationId: string, offerData: {
  pet_id: string;
  start_date: string;
  end_date: string;
  total_amount: number;
  notes?: string;
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post(`https://api.cvflow.tech/api/conversations/${conversationId}/offers`, offerData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 8. Respond to Offer
**POST** `/api/conversations/{conversation_id}/offers/{offer_id}/respond`
Accepts or rejects an offer in a conversation.

```typescript
const respondToOffer = async (conversationId: string, offerId: string, accept: boolean, message?: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post(`https://api.cvflow.tech/api/conversations/${conversationId}/offers/${offerId}/respond`, {
    accept, message
  }, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

---

## 🔔 Notifications (`/api/notifications`)

### 1. Get All Notifications
**GET** `/api/notifications`
Retrieves all notifications for the current user.

```typescript
const getAllNotifications = async (page: number = 1, perPage: number = 20) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get('https://api.cvflow.tech/api/notifications', {
    params: { page, per_page: perPage },
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 2. Get Unread Notifications
**GET** `/api/notifications/unread`
Retrieves only unread notifications for the user.

```typescript
const getUnreadNotifications = async () => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get('https://api.cvflow.tech/api/notifications/unread', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 3. Get Unread Count
**GET** `/api/notifications/count`
Gets the count of unread notifications.

```typescript
const getUnreadCount = async () => {
  const token = localStorage.getItem('authToken');
  const response = await axios.get('https://api.cvflow.tech/api/notifications/count', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data; // { "count": 5 }
};
```

### 4. Mark as Read
**PUT** `/api/notifications/{notification_id}/read`
Marks a specific notification as read.

```typescript
const markNotificationAsRead = async (notificationId: string) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.put(`https://api.cvflow.tech/api/notifications/${notificationId}/read`, {}, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 5. Mark All as Read
**PUT** `/api/notifications/read-all`
Marks all notifications as read for the user.

```typescript
const markAllAsRead = async () => {
  const token = localStorage.getItem('authToken');
  const response = await axios.put('https://api.cvflow.tech/api/notifications/read-all', {}, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

---

## ⭐ Reviews & Ratings (`/api/reviews`)

### 1. Create Review
**POST** `/api/reviews/{entity_type}/{entity_id}`
Creates a review for a pet, user, or booking.

```typescript
const createReview = async (entityType: 'pet' | 'user', entityId: string, reviewData: {
  rating: number;
  title: string;
  content: string;
  transaction_id?: string;
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post(`https://api.cvflow.tech/api/reviews/${entityType}/${entityId}`, reviewData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 2. Get Entity Reviews
**GET** `/api/reviews/{entity_type}/{entity_id}`
Gets all reviews for a specific entity (pet or user).

```typescript
const getEntityReviews = async (entityType: 'pet' | 'user', entityId: string, page: number = 1) => {
  const response = await axios.get(`https://api.cvflow.tech/api/reviews/${entityType}/${entityId}`, {
    params: { page }
  });
  return response.data;
};
```

### 3. Get Review Summary
**GET** `/api/reviews/{entity_type}/{entity_id}/summary`
Gets review statistics and summary for an entity.

```typescript
const getReviewSummary = async (entityType: 'pet' | 'user', entityId: string) => {
  const response = await axios.get(`https://api.cvflow.tech/api/reviews/${entityType}/${entityId}/summary`);
  return response.data;
};
```

**Response (200):**
```json
{
  "average_rating": 4.5,
  "total_reviews": 24,
  "rating_distribution": {
    "5": 12,
    "4": 8,
    "3": 3,
    "2": 1,
    "1": 0
  }
}
```

---

## 🚨 Reports (`/api/reports`)

### 1. Report User
**POST** `/api/reports/users/{user_id}`
Reports a user for inappropriate behavior.

```typescript
const reportUser = async (userId: string, reportData: {
  reason: string;
  details: string;
  evidence_urls?: string[];
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post(`https://api.cvflow.tech/api/reports/users/${userId}`, reportData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 2. Report Pet
**POST** `/api/reports/pets/{pet_id}`
Reports a pet listing for inappropriate content.

```typescript
const reportPet = async (petId: string, reportData: {
  reason: string;
  details: string;
  evidence_urls?: string[];
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post(`https://api.cvflow.tech/api/reports/pets/${petId}`, reportData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 3. Upload Report Evidence
**POST** `/api/reports/evidence`
Uploads evidence files for a report.

```typescript
const uploadReportEvidence = async (files: File[]) => {
  const token = localStorage.getItem('authToken');
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const response = await axios.post('https://api.cvflow.tech/api/reports/evidence', formData, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};
```

---

## 📅 Calendar & Availability (`/api/calendar`)

### 1. Get Pet Calendar
**GET** `/api/calendar/pets/{pet_id}`
Gets calendar data showing availability for a pet.

```typescript
const getPetCalendar = async (petId: string, startDate: string, endDate: string) => {
  const response = await axios.get(`https://api.cvflow.tech/api/calendar/pets/${petId}`, {
    params: { start_date: startDate, end_date: endDate }
  });
  return response.data;
};
```

### 2. Block Dates
**POST** `/api/calendar/pets/{pet_id}/blocked-dates`
Blocks specific dates for a pet (owner only).

```typescript
const blockDates = async (petId: string, blockData: {
  start_date: string;
  end_date: string;
  reason: string;
  notes?: string;
}) => {
  const token = localStorage.getItem('authToken');
  const response = await axios.post(`https://api.cvflow.tech/api/calendar/pets/${petId}/blocked-dates`, blockData, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.data;
};
```

### 3. Check Availability
**GET** `/api/calendar/availability/{pet_id}`
Checks if a pet is available for specific dates.

```typescript
const checkAvailability = async (petId: string, startDate: string, endDate: string) => {
  const response = await axios.get(`https://api.cvflow.tech/api/calendar/availability/${petId}`, {
    params: { start_date: startDate, end_date: endDate }
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
headers: {
  'Authorization': `Bearer ${token}`
}
```

Store the token after successful login/registration and include it in subsequent requests. 