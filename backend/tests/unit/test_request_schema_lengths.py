"""Mọi trường chuỗi của request model phải chặn độ dài — hoặc nằm trong danh sách
miễn trừ có lý do.

Vì sao cần cổng này: cột ``varchar(n)`` trên Postgres từ chối chuỗi dài hơn ``n``
(``StringDataRightTruncationError``) và request rớt **500**. Bộ test chạy trên SQLite —
SQLite **bỏ qua** độ dài khai báo — nên không có gì khác trong suite này bắt được.
Đã lọt thật: `POST /customers` với `full_name` 300 ký tự trả 500 trên Postgres trong
khi 734 test xanh (PROJECT_STATE §7aq).

Chặn ở tầng schema, KHÔNG bắt lỗi DB rồi đổi thành 4xx: bắt kiểu đó sẽ nuốt luôn các
ca chuỗi quá dài do **chính hệ thống** sinh ra — vốn là bug thật cần nổ to (chính một
lỗi như vậy đã lộ ra nhờ 500: `audit_logs.action`, migration `0023`).
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

from pydantic import BaseModel

import pharmacy_os

#: ``Model.field`` được miễn chặn độ dài, kèm lý do. Thêm dòng vào đây là một quyết
#: định có ý thức — mặc định của một trường chuỗi mới là PHẢI chặn.
_EXEMPT: dict[str, str] = {
    # Cột Text — Postgres không giới hạn nên không có ca truncation.
    "RecordControlledEntryRequest.note": "cột Text",
    "AddAllergyRequest.note": "cột Text",
    "AddConditionRequest.note": "cột Text",
    "PrescriptionItemRequest.instructions": "cột Text",
    "CreatePrescriptionRequest.diagnosis": "cột Text",
    "CreateSupplierRequest.address": "cột Text",
    "PushSyncRequest.payload": "không xuống cột nào — chỉ băm thành payload_hash",
    "ReturnedDrugItemRequest.description": "cột Text",
    "ReturnedDrugItemRequest.condition_note": "cột Text",
    "ReturnedDrugItemRequest.reason": "cột Text",
    # Bí mật: không lưu thô, nên không có cột để tràn. Chặn trên còn có hại — khoá cửa
    # người đặt mật khẩu rất dài (bcrypt vốn tự cắt ở 72 byte).
    "LoginRequest.password": "chỉ đi vào bcrypt",
    "CreateUserRequest.password": "chỉ đi vào bcrypt",
    "ResetPasswordRequest.new_password": "chỉ đi vào bcrypt",
    "ChangePasswordRequest.current_password": "chỉ đi vào bcrypt",
    "ChangePasswordRequest.new_password": "chỉ đi vào bcrypt",
    "SignLedgerBookRequest.current_password": "chỉ đi vào bcrypt (re-auth ký sổ, bước 6 TT18)",
    "RefreshRequest.refresh_token": "chỉ đi vào sha256",
    "SwitchBranchRequest.refresh_token": "chỉ đi vào sha256",
    # Ràng buộc nằm trong Annotated của phần tử (chặn độ dài TỪNG tên, không phải số
    # phần tử) nên không lộ ra ở metadata của chính trường.
    "CheckInteractionsRequest.ingredients": "chặn theo từng phần tử qua Annotated",
}


def _request_models() -> list[type[BaseModel]]:
    """Mọi model trong `*/interface/schemas.py` trừ phía trả về (dữ liệu ra từ DB đã
    bị cột ràng buộc sẵn, không phải đường vào)."""
    found: list[type[BaseModel]] = []
    for mod_info in pkgutil.walk_packages(pharmacy_os.__path__, "pharmacy_os."):
        if not mod_info.name.endswith("schemas"):
            continue
        module = importlib.import_module(mod_info.name)
        for name, obj in vars(module).items():
            if not (inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel):
                continue
            if obj.__module__ != mod_info.name:
                continue
            if "Response" in name or name.endswith(("Row", "Output")):
                continue
            found.append(obj)
    return found


def test_every_request_string_field_bounds_its_length() -> None:
    models = _request_models()
    assert models, "không quét được model nào — kiểm tra lại cách duyệt package"

    unbounded = []
    for model in models:
        for field_name, field in model.model_fields.items():
            if "str" not in str(field.annotation):
                continue
            key = f"{model.__name__}.{field_name}"
            if key in _EXEMPT:
                continue
            if not any(hasattr(m, "max_length") for m in field.metadata):
                unbounded.append(key)

    assert unbounded == [], (
        "trường chuỗi request không chặn độ dài (Postgres sẽ trả 500 thay vì 422): "
        f"{sorted(unbounded)}"
    )


def test_exempt_list_has_no_dead_entries() -> None:
    """Danh sách miễn trừ phải bám thực tế: trường đã đổi tên/xoá thì gỡ khỏi đây,
    đừng để tích tụ thành rác che mất trường mới thật sự thiếu chặn."""
    live = {f"{m.__name__}.{f}" for m in _request_models() for f in m.model_fields}
    assert sorted(set(_EXEMPT) - live) == []
