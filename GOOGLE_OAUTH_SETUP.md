# Google OAuth Setup Guide

## 🚀 Overview
This guide walks you through setting up Google OAuth authentication for your pet rental platform. Google OAuth allows users to sign in with their Google accounts instead of creating new passwords.

## 📋 Prerequisites
- Google Cloud Platform account
- Your application domain (for production)
- Access to your server's environment variables

## 🛠️ Google Cloud Console Setup

### Step 1: Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: `pet-rental-oauth` (or your preferred name)
4. Click "Create"

### Step 2: Enable Google+ API
1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google+ API" 
3. Click "Enable"
4. Also enable "Google Identity" if available

### Step 3: Configure OAuth Consent Screen
1. Go to "APIs & Services" → "OAuth consent screen"
2. Choose "External" (unless you have a G Suite domain)
3. Fill in the required information:
   - **App name**: Your Pet Rental Platform
   - **User support email**: Your support email
   - **App logo**: Upload your app logo (optional)
   - **App domain**: Your website domain
   - **Authorized domains**: Add your domain (e.g., `cvflow.tech`)
   - **Developer contact**: Your email address
4. Click "Save and Continue"

### Step 4: Add Scopes
1. Click "Add or Remove Scopes"
2. Add these scopes:
   - `../auth/userinfo.email`
   - `../auth/userinfo.profile` 
   - `openid`
3. Click "Update" → "Save and Continue"

### Step 5: Create OAuth 2.0 Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Choose "Web application"
4. Configure:
   - **Name**: Pet Rental OAuth Client
   - **Authorized JavaScript origins**:
     - `http://localhost:3000` (for development)
     - `https://yourdomain.com` (for production)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/api/auth/google/callback` (for development)
     - `https://api.yourdomain.com/api/auth/google/callback` (for production)
5. Click "Create"
6. **Save the Client ID and Client Secret** - you'll need these!

## 🔧 Environment Variables Setup

Add these variables to your `.env` file:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# For production, update the redirect URI:
# GOOGLE_REDIRECT_URI=https://api.yourdomain.com/api/auth/google/callback

# Frontend URL (where users get redirected after successful login)
FRONTEND_URL=http://localhost:3000
# For production: FRONTEND_URL=https://yourdomain.com
```

## 📋 Required Environment Variables

Here's the complete list of environment variables you need for the authentication system:

```bash
# Database
MONGODB_URI=mongodb://localhost:27017/pet_rental_db

# JWT Configuration  
JWT_SECRET_KEY=your_super_secret_jwt_key_here_make_it_long_and_random
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-1234567890123456789012345678901234
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# Frontend & API URLs
FRONTEND_URL=http://localhost:3000
API_BASE_URL=https://api.cvflow.tech

# Email Configuration (for password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@yourapp.com
```

## 🔗 API Endpoints

### 1. Get Google Auth URL
**GET** `/api/auth/google`

Returns the Google OAuth authorization URL for redirecting users.

```typescript
const getGoogleAuthUrl = async () => {
  const response = await fetch('/api/auth/google');
  const data = await response.json();
  // Redirect user to data.auth_url
  window.location.href = data.auth_url;
};
```

### 2. Google Login (API Response) ⭐ NEW
**POST** `/api/auth/google/login`

Professional endpoint that returns JWT token directly (no redirect).

```typescript
const googleLogin = async (authCode: string) => {
  const response = await fetch('/api/auth/google/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: authCode })
  });
  
  const data = await response.json();
  // data.access_token contains the JWT token
  localStorage.setItem('authToken', data.access_token);
  return data;
};
```

### 3. Google Callback (Redirect Flow)
**GET** `/api/auth/google/callback?code=...`

Handles the redirect from Google (for web applications).

### 4. Get Google User Info ⭐ NEW
**GET** `/api/auth/google/user-info?access_token=...`

Get user information from Google access token.

```typescript
const getGoogleUserInfo = async (googleAccessToken: string) => {
  const response = await fetch(`/api/auth/google/user-info?access_token=${googleAccessToken}`);
  return await response.json();
};
```

## 🎯 Integration Examples

### React/Next.js Integration

```typescript
// utils/googleAuth.ts
export const handleGoogleLogin = async () => {
  try {
    // Step 1: Get Google auth URL
    const response = await fetch('/api/auth/google');
    const { auth_url } = await response.json();
    
    // Step 2: Open popup or redirect
    const popup = window.open(auth_url, 'google-login', 'width=500,height=600');
    
    // Step 3: Listen for callback (you'll need to implement this)
    // When you get the auth code, call the login endpoint
    
  } catch (error) {
    console.error('Google login failed:', error);
  }
};

// Alternative: Direct redirect approach
export const redirectToGoogle = async () => {
  const response = await fetch('/api/auth/google');
  const { auth_url } = await response.json();
  window.location.href = auth_url;
};
```

### Mobile App Integration

```typescript
// For React Native or mobile apps
import { GoogleSignin } from '@react-native-google-signin/google-signin';

const mobileGoogleLogin = async () => {
  try {
    // Configure Google Sign-In
    await GoogleSignin.configure({
      webClientId: 'your_google_client_id_here',
    });
    
    // Sign in with Google
    const { serverAuthCode } = await GoogleSignin.signIn();
    
    // Send server auth code to your API
    const response = await fetch('/api/auth/google/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: serverAuthCode })
    });
    
    const { access_token } = await response.json();
    // Store the JWT token
    await AsyncStorage.setItem('authToken', access_token);
    
  } catch (error) {
    console.error('Mobile Google login failed:', error);
  }
};
```

## 🔒 Security Best Practices

### 1. Environment Security
- Never commit `.env` files to version control
- Use different credentials for development/production
- Rotate secrets regularly

### 2. Domain Configuration
- Always specify exact authorized domains
- Use HTTPS in production
- Whitelist only necessary redirect URIs

### 3. Token Handling
- Store JWT tokens securely (httpOnly cookies preferred)
- Implement token refresh logic
- Set appropriate token expiration times

## 🚀 Production Deployment

### Update Environment Variables
```bash
# Production environment variables
GOOGLE_CLIENT_ID=your_production_google_client_id
GOOGLE_CLIENT_SECRET=your_production_google_client_secret  
GOOGLE_REDIRECT_URI=https://api.yourdomain.com/api/auth/google/callback
FRONTEND_URL=https://yourdomain.com
API_BASE_URL=https://api.yourdomain.com
```

### Google Cloud Console Updates
1. Add production domains to authorized origins
2. Add production callback URLs to redirect URIs
3. Update OAuth consent screen with production domain
4. Submit for verification if needed (for large user bases)

## 🔧 Troubleshooting

### Common Issues

**Error: "redirect_uri_mismatch"**
- Check that your redirect URI exactly matches what's configured in Google Cloud Console
- Ensure you're using the correct protocol (http vs https)

**Error: "access_denied"**
- User cancelled the authorization
- Check OAuth consent screen configuration

**Error: "invalid_client"**
- Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correct
- Ensure the OAuth client is configured for web application

**Error: "unauthorized_client"**
- Check that your domain is authorized in Google Cloud Console
- Verify the client is enabled for the Google+ API

### Debug Mode
Set logging level to DEBUG to see detailed OAuth flow logs:

```python
import logging
logging.getLogger("utils.google_oauth").setLevel(logging.DEBUG)
```

## ✅ Testing

### Test the Flow
1. Start your server: `uvicorn main:app --reload`
2. Navigate to: `http://localhost:8000/api/auth/google`
3. Complete the Google OAuth flow
4. Check that you're redirected with a token

### API Testing
```bash
# Test getting auth URL
curl http://localhost:8000/api/auth/google

# Test user info endpoint (with actual Google access token)
curl "http://localhost:8000/api/auth/google/user-info?access_token=YOUR_GOOGLE_ACCESS_TOKEN"
```

## 📞 Support

If you encounter issues:
1. Check the server logs for detailed error messages
2. Verify all environment variables are set correctly
3. Ensure Google Cloud Console configuration matches your setup
4. Test with a fresh browser session (clear cookies/cache)

---

**🎉 Congratulations!** Your Google OAuth integration is now ready. Users can sign in with their Google accounts seamlessly! 