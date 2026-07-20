# 11 — THIẾT KẾ API (API Design)

> REST versioned `/api/v1`, JSON, OpenAPI tự sinh (FastAPI). WebSocket cho realtime & AI streaming.

---

## 1. Nguyên tắc API

1. **Versioned**: tiền tố `/api/v1`. Thay đổi phá vỡ → `/api/v2`.
2. **Resource-oriented**: danh từ số nhiều (`/sales-orders`, `/drugs`).
3. **Idempotency**: `Idempotency-Key` header (hoặc `client_uuid` body) cho POS offline.
4. **Tenant/branch**: lấy từ JWT + header `X-Branch-Id`; không nhận từ query tùy tiện.
5. **Envelope lỗi chuẩn** RFC 7807 (problem+json).
6. **Phân trang** cursor-based cho danh sách lớn.
7. **RBAC**: mỗi endpoint gắn permission code.

---

## 2. Chuẩn response

**Thành công:**
```json
{
  "data": { "...": "..." },
  "meta": { "request_id": "uuid" }
}
```

**Danh sách:**
```json
{
  "data": [ ],
  "meta": { "next_cursor": "opaque", "count": 20 }
}
```

**Lỗi (RFC 7807):**
```json
{
  "type": "https://errors.pharmacy-os/validation",
  "title": "Dữ liệu không hợp lệ",
  "status": 422,
  "detail": "quantity phải > 0",
  "instance": "/api/v1/sales-orders",
  "errors": [ { "field": "items[0].quantity", "msg": "must be > 0" } ]
}
```

---

## 3. Bản đồ endpoint (v1) theo module

### iam
| Method | Path | Permission |
|--------|------|-----------|
| POST | `/auth/login` | public |
| POST | `/auth/refresh` | public |
| GET | `/users` | `iam.user.read` |
| POST | `/users` | `iam.user.create` |
| GET/PUT | `/roles`, `/roles/{id}` | `iam.role.*` |

### catalog
| Method | Path | Permission |
|--------|------|-----------|
| GET | `/drugs?query=&cursor=` | `catalog.read` |
| POST | `/drugs` | `catalog.create` |
| GET | `/drugs/{id}` | `catalog.read` |
| GET | `/drugs/{id}/units` | `catalog.read` |

### inventory
| Method | Path | Permission |
|--------|------|-----------|
| GET | `/batches?drug_id=&near_expiry=` | `inventory.read` |
| GET | `/stock-balances?drug_id=` | `inventory.read` |
| POST | `/stock-takes` | `inventory.stocktake` |
| POST | `/stock-transfers` | `inventory.transfer` |
| GET | `/inventory/alerts` | `inventory.read` |

### sales
| Method | Path | Permission |
|--------|------|-----------|
| POST | `/sales-orders` (Idempotency-Key) | `sales.create` |
| POST | `/sales-orders/{id}/payments` | `sales.pay` |
| POST | `/sales-orders/{id}/complete` | `sales.create` |
| POST | `/sales-orders/{id}/return` | `sales.return` |
| POST | `/sync/sales` (batch offline) | `sales.create` |

### prescription
| Method | Path | Permission |
|--------|------|-----------|
| POST | `/prescriptions` | `rx.create` |
| POST | `/prescriptions/extract` (ảnh → AI) | `rx.create` |
| POST | `/prescriptions/{id}/validate` | `rx.approve` |
| POST | `/prescriptions/{id}/dispense` | `rx.dispense` |

### clinical / AI
| Method | Path | Permission |
|--------|------|-----------|
| POST | `/clinical/interaction-check` | `clinical.check` |
| POST | `/clinical/dose-check` | `clinical.check` |
| POST | `/clinical/substitutes` | `clinical.check` |
| WS | `/clinical/assistant` (streaming) | `clinical.chat` |

### procurement
| Method | Path | Permission |
|--------|------|-----------|
| GET/POST | `/suppliers` | `procurement.*` |
| POST | `/purchase-orders` | `procurement.po.create` |
| POST | `/goods-receipts` | `procurement.grn.create` |

### crm
| Method | Path | Permission |
|--------|------|-----------|
| GET/POST | `/customers` | `crm.*` |
| POST | `/customers/{id}/allergies` | `crm.update` |
| GET | `/customers/{id}/history` | `crm.read` |

### compliance
| Method | Path | Permission |
|--------|------|-----------|
| GET | `/compliance/controlled-ledger` | `compliance.read` |
| GET | `/compliance/audit-logs` | `compliance.audit` |
| POST | `/compliance/submissions/retry` | `compliance.submit` |

### analytics
| Method | Path | Permission |
|--------|------|-----------|
| GET | `/analytics/dashboard` | `analytics.read` |
| GET | `/analytics/forecast?drug_id=` | `analytics.read` |
| GET | `/analytics/reorder-suggestions` | `analytics.read` |

---

## 4. Ví dụ — Tạo đơn bán (idempotent)

**Request**
```http
POST /api/v1/sales-orders
Authorization: Bearer <jwt>
X-Branch-Id: <uuid>
Idempotency-Key: 0192f...   # = client_uuid từ POS

{
  "customer_id": null,
  "prescription_id": null,
  "items": [
    { "drug_id": "…", "quantity": 2, "unit": "vỉ" }
  ],
  "payment": { "method": "CASH", "amount": 45000 }
}
```

**Response 201**
```json
{
  "data": {
    "id": "…",
    "status": "COMPLETED",
    "total": 45000,
    "invoice_no": "HD-2026-000123",
    "ai_warnings": []
  },
  "meta": { "request_id": "…" }
}
```

Gọi lại cùng `Idempotency-Key` → trả về đúng đơn đã tạo (không nhân đôi).

---

## 5. AI streaming (WebSocket)

```text
WS /api/v1/clinical/assistant
→ client gửi: { "type":"ask", "content":"tương tác warfarin + aspirin?" }
← server stream: { "type":"token", "content":"..." } (nhiều lần)
← server: { "type":"done", "sources":[...], "confidence":0.82 }
```

---

## 6. Bảo mật & giới hạn

- **Auth**: Bearer JWT (access ngắn hạn) + refresh token.
- **Rate limit**: theo user + endpoint (Redis).
- **Audit**: mọi POST/PUT/DELETE nhạy cảm ghi `audit_logs`.
- **Validation**: Pydantic ở biên; domain rules ở trong.
- **CORS**: whitelist origin FE.

---

## 7. Tài liệu hóa

- OpenAPI tự sinh tại `/api/v1/docs` (Swagger) & `/api/v1/redoc`.
- Schema xuất `openapi.json` để FE sinh client type-safe (zod/openapi-typescript).
