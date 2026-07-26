"""encrypt_crm_pii — SĐT + dữ liệu sức khoẻ KH sang Text, thêm blind index (Sprint 8 mục 3/4)

Ba việc, không đụng dữ liệu sẵn có:

1. ``customers.phone``, ``customers.gender``, ``customer_conditions.condition_code`` →
   ``text`` cho ciphertext (lý do chọn ``text`` thay vì đoán ``varchar`` rộng hơn: xem
   migration ``0030``). ``customer_allergies.note``/``customer_conditions.note`` vốn đã
   là ``text`` nên không cần đổi kiểu — chỉ đổi hành vi ở tầng ứng dụng.
2. Thêm ``customers.phone_fingerprint`` + index: **thay thế chức năng** của
   ``ix_customers_phone``. Mã hoá phá đẳng thức (ciphertext khác nhau mỗi lần ghi), nên
   ``WHERE phone = ?`` sẽ không bao giờ khớp; ``find_by_phone`` chuyển sang so khớp
   fingerprint. Cột nullable: deployment chưa có khoá index thì để trống và tra cứu lùi
   về so sánh cột ``phone`` trực tiếp.
3. Bỏ ``ix_customers_phone``: index trên một cột ciphertext ngẫu nhiên không phục vụ
   truy vấn nào nữa, chỉ tốn ghi.

**KHÔNG mã hoá trong đợt này, có lý do, không phải bỏ sót:**

* ``customers.full_name`` — ``list()`` đang ``ORDER BY full_name``. Ciphertext sắp xếp
  ngẫu nhiên ⇒ mã hoá sẽ **âm thầm phá phân trang theo bảng chữ cái**, mà blind index
  không cứu được (fingerprint giữ được *đẳng thức*, không giữ được *thứ tự*). Cần quyết
  định nghiệp vụ: có chấp nhận bỏ sắp xếp theo tên không.
* ``customers.dob``/``weight_kg`` — cột ``date``/``numeric``, mã hoá buộc phải đổi sang
  text và mất kiểu, đổi lấy PII yếu hơn SĐT.
* ``customer_allergies.ingredient_id`` — là **khoá ngoại** và là thứ
  ``find_allergy_alerts`` so khớp. Sự thật y tế cốt lõi ("dị ứng hoạt chất nào") vì vậy
  vẫn nằm dạng rõ; muốn mã hoá phải bỏ FK + thiết kế lại đối chiếu dị ứng — việc riêng,
  không nhét vào lát hardening này.

Revision ID: 0031_encrypt_crm_pii
Revises: 0030_encrypt_compliance_pii
Create Date: 2026-07-26 01:05:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_encrypt_crm_pii"
down_revision: str | None = "0030_encrypt_compliance_pii"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (bảng, cột, độ rộng varchar cũ, nullable) — một nguồn cho cả hai chiều.
_COLUMNS: tuple[tuple[str, str, int, bool], ...] = (
    ("customer_conditions", "condition_code", 16, False),
    ("customers", "phone", 32, True),
    ("customers", "gender", 16, True),
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
    op.add_column("customers", sa.Column("phone_fingerprint", sa.String(length=64), nullable=True))
    op.create_index("ix_customers_phone_fingerprint", "customers", ["phone_fingerprint"])
    op.drop_index("ix_customers_phone", table_name="customers")


def downgrade() -> None:
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.drop_index("ix_customers_phone_fingerprint", table_name="customers")
    op.drop_column("customers", "phone_fingerprint")
    for table, column, width, nullable in _COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.Text(),
            type_=sa.String(length=width),
            existing_nullable=nullable,
        )
