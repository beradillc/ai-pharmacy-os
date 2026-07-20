# 07 — UML

> Class diagrams, state machines, component diagrams. Thiết kế mức khái niệm cho domain.

---

## 1. Class Diagram — Core Kernel

```mermaid
classDiagram
    class RequestContext {
        +UUID tenant_id
        +UUID branch_id
        +UUID user_id
        +list~str~ permissions
    }

    class EventBus {
        <<interface>>
        +publish(event: DomainEvent)
        +subscribe(type, handler)
    }

    class DomainEvent {
        <<abstract>>
        +UUID id
        +datetime occurred_at
        +UUID tenant_id
    }

    class UnitOfWork {
        <<interface>>
        +commit()
        +rollback()
        +repository(name)
    }

    class LLMProvider {
        <<interface>>
        +complete(prompt, tools) LLMResult
        +embed(text) Vector
    }

    class PluginLoader {
        +discover() list~Plugin~
        +load(plugin)
        +hooks(name) list
    }

    EventBus --> DomainEvent
    LLMProvider ..> DomainEvent : logs via AI Gateway
```

---

## 2. Class Diagram — Domain `sales`

```mermaid
classDiagram
    class SalesOrder {
        +UUID id
        +UUID client_uuid
        +UUID branch_id
        +UUID? customer_id
        +UUID? prescription_id
        +OrderStatus status
        +Money subtotal
        +Money vat
        +Money total
        +add_item(item)
        +complete()
        +ensure_rx_for_etc()
    }

    class SalesOrderItem {
        +UUID id
        +UUID drug_id
        +UUID batch_id
        +Quantity quantity
        +Money unit_price
        +line_total() Money
    }

    class Money {
        <<value object>>
        +Decimal amount
        +str currency
        +add(o) Money
    }

    class Quantity {
        <<value object>>
        +Decimal value
        +str unit
    }

    class SaleCompleted {
        <<domain event>>
        +UUID order_id
        +list items
    }

    class SalesRepository {
        <<interface / port>>
        +add(order)
        +get(id) SalesOrder
        +by_client_uuid(uuid) SalesOrder?
    }

    SalesOrder "1" *-- "many" SalesOrderItem
    SalesOrderItem --> Money
    SalesOrderItem --> Quantity
    SalesOrder ..> SaleCompleted : emits
    SalesOrder ..> SalesRepository : persisted by
```

---

## 3. Class Diagram — Domain `inventory` (event-sourced)

```mermaid
classDiagram
    class ProductBatch {
        +UUID id
        +UUID drug_id
        +str lot_no
        +date expiry_date
        +Money cost_price
        +is_expired(on) bool
    }

    class StockMovement {
        +UUID id
        +MovementType type
        +Quantity quantity
        +str ref_type
        +UUID ref_id
        +datetime occurred_at
    }

    class StockBalance {
        +UUID drug_id
        +UUID batch_id
        +Decimal quantity
    }

    class FefoAllocator {
        +allocate(drug_id, qty, branch) list~Allocation~
    }

    class MovementType {
        <<enumeration>>
        IN
        OUT
        ADJUST
        TRANSFER
    }

    ProductBatch "1" o-- "many" StockMovement
    StockMovement --> MovementType
    StockMovement ..> StockBalance : projects to
    FefoAllocator ..> ProductBatch : reads
```

---

## 4. State Machine — Prescription

```mermaid
stateDiagram-v2
    [*] --> DRAFT: tiếp nhận
    DRAFT --> VALIDATED: dược sĩ xác thực
    DRAFT --> REJECTED: đơn không hợp lệ
    VALIDATED --> DISPENSED: cấp phát
    VALIDATED --> REJECTED: phát hiện rủi ro
    DISPENSED --> [*]
    REJECTED --> [*]
```

---

## 5. State Machine — SalesOrder

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> PENDING_PAYMENT: chốt giỏ
    PENDING_PAYMENT --> COMPLETED: thanh toán OK
    PENDING_PAYMENT --> CANCELLED: hủy
    COMPLETED --> RETURNED: trả hàng (có duyệt)
    COMPLETED --> [*]
    CANCELLED --> [*]
    RETURNED --> [*]
```

---

## 6. State Machine — Purchase Order

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> ORDERED: gửi NCC
    ORDERED --> PARTIALLY_RECEIVED: nhận một phần
    ORDERED --> RECEIVED: nhận đủ
    PARTIALLY_RECEIVED --> RECEIVED
    RECEIVED --> CLOSED
    DRAFT --> CANCELLED
    CLOSED --> [*]
    CANCELLED --> [*]
```

---

## 7. Component Diagram — Module & Kernel

```mermaid
graph TB
    subgraph Kernel
        BUS[EventBus]
        DI[DI Container]
        AIGW[AI Gateway]
        PLG[Plugin Loader]
        AUTH[Auth/RBAC]
    end

    subgraph Modules
        CAT[catalog]
        INV[inventory]
        SAL[sales]
        RX[prescription]
        CLI[clinical]
        CRM[crm]
        PRO[procurement]
        COM[compliance]
        ANA[analytics]
        IAM[iam]
    end

    SAL -- emits --> BUS
    RX -- emits --> BUS
    BUS -- notifies --> INV
    BUS -- notifies --> CRM
    BUS -- notifies --> COM
    CLI -- uses --> AIGW
    RX -- uses --> AIGW
    COM -- uses --> PLG
    SAL -- uses --> PLG
    Modules -- guarded by --> AUTH
```

---

## 8. Sequence — Use-case `CreateSale` (chi tiết Hexagonal)

```mermaid
sequenceDiagram
    participant R as interface/router
    participant UC as application/CreateSale
    participant DOM as domain/SalesOrder
    participant REPO as infra/SalesRepository
    participant UOW as core/UnitOfWork
    participant BUS as core/EventBus

    R->>UC: execute(dto, context)
    UC->>DOM: SalesOrder.create(...)
    DOM->>DOM: ensure_rx_for_etc()
    UC->>REPO: add(order)
    UC->>UOW: commit()
    UOW->>BUS: publish(SaleCompleted)
    UC-->>R: SaleResult
```

---

## 9. Ghi chú UML

- UML ở đây là **mức thiết kế khái niệm**; chữ ký phương thức có thể tinh chỉnh khi hiện thực.
- Value Objects (`Money`, `Quantity`) là bất biến (immutable).
- Aggregate roots: `SalesOrder`, `Prescription`, `ProductBatch`(qua movements), `PurchaseOrder`.
- Diagram nguồn (`.mmd`) sẽ được tách vào `docs/uml/` ở Sprint 2 để CI render.
