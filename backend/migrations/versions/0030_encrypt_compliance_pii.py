"""encrypt_compliance_pii — PII compliance sang Text cho ciphertext (Sprint 8 mục 3/4)

``varchar(n)`` → ``text``, **không đụng dữ liệu**. Mã hoá là việc của tầng ứng dụng
(``EncryptedText``); CSDL chỉ thấy ``text``, nên migration dùng ``sa.Text()`` thuần —
Alembic tự sinh tham chiếu ``pharmacy_os.core.db.encrypted_types.EncryptedText()`` mà
**không import** (chạy sẽ ``NameError``), và gắn kiểu tầng ứng dụng vào lịch sử migration
là buộc migration cũ phụ thuộc code mới vĩnh viễn.

**Vì sao ``text`` chứ không phải ``varchar`` rộng hơn:** ciphertext dài hơn bản rõ ~4/3
lần cộng nonce+tag, mà tiếng Việt có dấu chiếm 3 byte/ký tự — đoán một con số ở đây là tự
chuốc ``StringDataRightTruncation`` (500) trên Postgres mà SQLite không tái hiện
(PROJECT_STATE §7ap/§7aq). ``text`` xoá hẳn cả lớp lỗi đó. Giới hạn độ dài **bản rõ** vẫn
nguyên ở tầng schema (``RecordControlledEntryRequest``/``RecordDrugReturnRequest``), nên
không mất kiểm tra đầu vào nào. Trên Postgres ``varchar(n)``→``text`` không phải viết lại
bảng.

Cột được mã hoá: tên/địa chỉ bệnh nhân mua thuốc kiểm soát đặc biệt (PL XIX) và toàn bộ
thông tin người trả thuốc (PL XVIII) — gồm **số CCCD**, PII mạnh nhất hệ thống.

**Đã kiểm: không cột nào trong số này nằm trong CSV sổ được ký** (mẫu PL VIII/XVI chỉ 8
cột + ``drug_id``), nên mã hoá không thể làm sai lệch ``content_sha256`` của chữ ký pháp
lý đã lập — rủi ro sắc nhất của mục này đã được LOẠI TRỪ bằng kiểm chứng, không phải bỏ qua.

**Downgrade** đưa về ``varchar(n)`` cũ và sẽ **thất bại** (không cắt cụt âm thầm) nếu cột
đang chứa ciphertext dài hơn giới hạn. Đó là hành vi đúng: muốn lùi thật thì phải giải mã
về bản rõ trước.

Revision ID: 0030_encrypt_compliance_pii
Revises: 0029_encrypt_two_factor_secret
Create Date: 2026-07-26 00:46:45.090286+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_encrypt_compliance_pii"
down_revision: str | None = "0029_encrypt_two_factor_secret"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (bảng, cột, độ rộng varchar cũ, nullable) — một nguồn duy nhất cho cả hai chiều, để
#: upgrade và downgrade không thể lệch nhau khi sửa về sau.
_COLUMNS: tuple[tuple[str, str, int, bool], ...] = (
    ("controlled_ledger_entries", "customer_name", 255, True),
    ("controlled_ledger_entries", "customer_address", 500, True),
    ("drug_return_records", "returner_name", 255, False),
    ("drug_return_records", "returner_address", 500, False),
    ("drug_return_records", "returner_id_number", 32, False),
    ("drug_return_records", "returner_id_issuer", 255, False),
    ("drug_return_records", "receiving_pharmacist_name", 255, False),
)


def upgrade() -> None:
    for table, column, width, nullable in _COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=width),
            type_=sa.Text(),
            existing_nullable=nullable,
        )


def downgrade() -> None:
    for table, column, width, nullable in _COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.Text(),
            type_=sa.String(length=width),
            existing_nullable=nullable,
        )
