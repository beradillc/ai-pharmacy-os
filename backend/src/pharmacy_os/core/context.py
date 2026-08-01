"""Per-request execution context (tenant, branch, actor, permissions).

Carried explicitly through use-cases rather than pulled from globals, so the
domain stays testable. The API layer builds it from the JWT + ``X-Branch-Id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RequestContext:
    tenant_id: UUID
    branch_id: UUID
    user_id: UUID
    permissions: frozenset[str] = field(default_factory=frozenset)

    client_ip: str | None = None
    """Origin of the request, filled by the API layer for the audit trail only.

    Optional and defaulted so service-level callers and tests need not supply one,
    and so it can never be mistaken for an authorisation input — nothing branches
    on it.
    """

    user_agent: str | None = None
    """Thiết bị/trình duyệt đã gửi request, cho sổ audit và **chỉ** cho sổ audit
    (UAT lỗi M-06, 2026-08-01).

    Vì sao cần bên cạnh :attr:`client_ip`: trong một nhà thuốc mọi máy đi chung một
    đường truyền, nên IP trả lời được *"từ đâu"* nhưng không trả lời được *"từ máy
    nào"* — mà khi sổ lệch, câu hỏi thật là *"máy quầy hay điện thoại của ai đó ở
    nhà"*. Hai trường trả lời hai câu khác nhau và không suy ra nhau được.

    Cùng kỷ luật với ``client_ip``: **không có gì rẽ nhánh trên nó**. Chuỗi này do
    client gửi nên hoàn toàn giả mạo được — nó là *manh mối*, không phải *bằng chứng*,
    và dùng nó để cấp quyền thì đúng bằng không cấp quyền gì cả.
    """

    def has(self, permission: str) -> bool:
        return permission in self.permissions

    @property
    def audit_meta(self) -> dict[str, str | None]:
        """Siêu dữ liệu request mà **mọi** dòng audit nên mang.

        Tồn tại để các call site không phải nhớ liệt kê từng trường: thêm
        ``user_agent`` (M-06) đáng lẽ phải sửa 23 chỗ, và chỗ nào quên thì
        **không cổng nào đỏ** — dòng audit vẫn ghi được, chỉ thiếu lặng lẽ. Đó
        đúng hình dạng kỷ luật #22. Nay chỗ duy nhất phải sửa là đây.

        ``AuditEntry.with_context`` bỏ giá trị ``None``, nên một request không có
        User-Agent đơn giản là không có khoá ấy — không lưu chuỗi rỗng.
        """
        return {"client_ip": self.client_ip, "user_agent": self.user_agent}
