# API Reference — Phase 0.1

Base URL: `http://localhost:8000/api/v1`

All endpoints return the standard envelope:
```json
{ "success": true, "data": {}, "message": "", "request_id": "" }
```

Authentication: `Authorization: Bearer <token>`

---

## Authentication

### POST /auth/register
Create a new account.

**Body:**
```json
{ "email": "user@example.com", "username": "learner42", "password": "securepass" }
```

**Response 201:**
```json
{ "success": true, "data": { "user": {...}, "token": "eyJ..." }, "message": "Account created successfully", "request_id": "..." }
```

---

### POST /auth/login
Sign in to an existing account.

**Body:**
```json
{ "email": "user@example.com", "password": "securepass" }
```

**Response 200:**
```json
{ "success": true, "data": { "user": {...}, "token": "eyJ..." }, "message": "Login successful", "request_id": "..." }
```

---

### POST /auth/logout
Invalidate the current session (client-side token discard).

**Auth required:** Yes

**Response 200:**
```json
{ "success": true, "data": {}, "message": "Logged out successfully", "request_id": "..." }
```

---

### GET /auth/me
Return the currently authenticated user.

**Auth required:** Yes

**Response 200:**
```json
{ "success": true, "data": { "id": "...", "email": "...", "username": "...", "is_active": true, "is_verified": false, "created_at": "...", "updated_at": "..." }, "message": "", "request_id": "..." }
```

---

## User

### GET /profile
Return the authenticated user's profile.

**Auth required:** Yes

**Response 200:**
```json
{ "success": true, "data": { "id": "...", "user_id": "...", "full_name": null, "avatar_url": null, "bio": null, "timezone": "UTC", "language": "en", "created_at": "...", "updated_at": "..." }, "message": "", "request_id": "..." }
```

---

### PUT /profile
Update profile fields.

**Auth required:** Yes

**Body (all optional):**
```json
{ "full_name": "Jane Doe", "bio": "Learning everything.", "timezone": "America/New_York", "language": "en" }
```

---

### GET /settings
Return the authenticated user's settings.

**Auth required:** Yes

---

### PUT /settings
Update settings.

**Auth required:** Yes

**Body (all optional):**
```json
{ "theme": "dark", "notifications_enabled": true, "llm_model": "llama-3.3-70b-versatile", "temperature": 0.7 }
```

---

## Chat

### POST /chat
Send a message and receive a streaming SSE response.

**Auth required:** Yes

**Body:**
```json
{ "message": "Explain recursion", "conversation_id": null }
```

**Response:** `text/event-stream`

```
data: {"type":"meta","conversation_id":"uuid"}
data: {"type":"chunk","content":"Recursion "}
data: {"type":"chunk","content":"is when..."}
data: {"type":"done","message_id":"uuid"}
```

---

### GET /chat/history
List conversations (paginated).

**Auth required:** Yes

**Query params:** `page=1&limit=20`

**Response 200:**
```json
{ "success": true, "data": [...], "meta": { "page": 1, "limit": 20, "total": 5, "total_pages": 1, "has_next": false, "has_prev": false }, "request_id": "..." }
```

---

### GET /chat/history/{id}
Get a single conversation with all messages.

**Auth required:** Yes

---

### DELETE /chat/history/{id}
Delete a conversation and all its messages.

**Auth required:** Yes

---

## System

### GET /health
Returns system health status.

**Response 200:**
```json
{ "success": true, "data": { "status": "healthy", "database": "up", "cache": "up", "uptime_seconds": 42.1 }, "request_id": "..." }
```

---

### GET /version
Returns app version and environment.

**Response 200:**
```json
{ "success": true, "data": { "version": "0.1.0", "env": "development" }, "request_id": "..." }
```

---

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| UNAUTHORIZED | 401 | Invalid or missing token |
| FORBIDDEN | 403 | Authenticated but not permitted |
| NOT_FOUND | 404 | Resource does not exist |
| DUPLICATE | 409 | Email or username already taken |
| VALIDATION_ERROR | 422 | Request body failed validation |
| RATE_LIMITED | 429 | Too many requests |
| LLM_ERROR | 502 | Upstream LLM provider error |
| INTERNAL_ERROR | 500 | Unexpected server error |
