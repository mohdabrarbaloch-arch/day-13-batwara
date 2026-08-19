# API Reference

Base URL: `http://localhost:8000` (dev) — all JSON. Auth endpoints return a
JWT; pass it as `Authorization: Bearer <token>` for protected routes.

## Auth

### POST /api/auth/register
Create an account.

```json
{ "name": "Ali Ahmed", "email": "ali@example.com", "password": "secret123" }
```
→ `201` `{ "access_token": "...", "token_type": "bearer", "user": {...} }`
- `409` if email already registered
- `422` if password < 8 chars or lacks letters/digits

### POST /api/auth/login
```json
{ "email": "ali@example.com", "password": "secret123" }
```
→ `200` token + user · `401` on bad credentials

### GET /api/auth/me
→ `200` current user

## Groups (JWT required)

### POST /api/groups
```json
{ "name": "Road Trip", "description": "Aug 2026", "currency": "PKR",
  "member_emails": ["bilal@example.com"] }
```
→ `201` group with members · non-registered emails are silently skipped

### GET /api/groups
→ `200` list of my groups (with `total_expenses`)

### GET /api/groups/{id}
→ `200` group detail · `403` non-member · `404` not found

### POST /api/groups/{id}/members
```json
["bilal@example.com", "sara@example.com"]
```
→ `201` updated group

### POST /api/groups/{id}/leave
→ `200` updated group

## Expenses (JWT required)

### POST /api/groups/{id}/expenses
Equal split:
```json
{ "description": "Dinner", "amount": 3000, "split_type": "equal" }
```
Exact split:
```json
{ "description": "Dinner", "amount": 1000, "split_type": "exact",
  "split_details": {"1": 500, "2": 300, "3": 200} }
```
→ `201` expense · `400` if exact shares don't sum to amount · `403` non-member

### GET /api/groups/{id}/expenses
→ `200` list (newest first), each with `per_person_share` and `your_share`

### DELETE /api/groups/{id}/expenses/{expense_id}
→ `204` · `403` if not the payer

## Settlements (JWT required)

### GET /api/groups/{id}/settle/balances
→ `200` per-member `{ paid, owes, net }` (net > 0 = gets back)

### GET /api/groups/{id}/settle/plan
→ `200`:
```json
{ "group_id": 1, "total_expenses": 4500, "algorithm": "optimal",
  "transactions": 1,
  "balances": [...], "plan": [ { "from_user": {...}, "to_user": {...}, "amount": 1500 } ] }
```

### POST /api/groups/{id}/settle
Record a settlement:
```json
{ "to_user_id": 3, "amount": 1500, "note": "JazzCash" }
```
→ `201` · `400` if recipient not a member / self-settlement

### GET /api/groups/{id}/settle/history
→ `200` list of recorded settlements (newest first)

## Health

### GET /api/health
→ `200` `{ "status": "ok", "app": "Batwara", "version": "1.0.0" }`

## Errors

All errors return `{ "detail": "..." }` with the appropriate status code:
`400` validation/conflict, `401` auth, `403` permissions, `404` missing,
`409` duplicate, `422` schema, `429` rate limit.
