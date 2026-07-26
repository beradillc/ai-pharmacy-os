# Hook cưỡng chế cổng chất lượng

Dựng 2026-07-26 theo audit **F-1** (`docs/audit/2026-07-26_BAO_CAO_KIEM_TOAN.md` mục 7.1).

## Cài (bắt buộc 1 lần trên mỗi máy)

```bash
make hooks
```

`core.hooksPath` là cấu hình **cục bộ**, không đi theo `git clone`. Đây đúng là cách
`.github/workflows/ci.yml` đã nằm chết trong repo suốt 209 commit (audit **C-03**): file có
sẵn, đúng nội dung, không ai nối dây. Máy mới mà quên `make hooks` thì quay lại đúng trạng
thái không có cưỡng chế — **không có tín hiệu nào báo điều đó**, nên kiểm bằng mục dưới.

## ⚠️ TỰ KIỂM CHỨNG — đừng tin phần trên

Toàn bộ đợt kiểm toán 2026-07-26 xoay quanh đúng một điểm: **lời khai "cổng xanh" không
thay được việc chạy thật.** File này nói hook có răng; điều đó cũng chỉ là một lời khai.
Chạy 4 lệnh sau để tự thấy — mất khoảng 20 giây, không để lại dấu vết gì.

```bash
# 1. Tạo một file Python cố tình sai (biến không dùng → ruff F841)
cat > /tmp/hook_test.py <<'EOF'
def broken() -> None:
    unused_variable = 42
EOF
cp /tmp/hook_test.py ./hook_test.py

# 2. Stage + thử commit → PHẢI BỊ CHẶN
git add hook_test.py
git commit -m "test: hook phải chặn commit này"
#    → mong đợi: "✗ ruff check" + "── COMMIT BỊ CHẶN ──", và commit KHÔNG được tạo

# 3. Xác nhận commit thật sự không tồn tại
git log --oneline -1        # phải vẫn là commit cũ, không phải "test: hook phải chặn..."

# 4. Dọn
git restore --staged hook_test.py && rm hook_test.py /tmp/hook_test.py
```

**Nếu bước 2 commit thành công** ⇒ hook chưa được cài. Kiểm:

```bash
git config --get core.hooksPath     # phải in ra: scripts/hooks
ls -l scripts/hooks/pre-commit      # phải có quyền thực thi (-rwxr-xr-x)
```

## Cổng nào chạy, cổng nào không

| Cổng | Trong hook? | Thời gian đo thật |
|---|:---:|---|
| `ruff check .` (toàn repo) | ✅ | 0,04s |
| `ruff format --check .` (toàn repo) | ✅ | 0,01s |
| `lint-imports` (18 contract) | ✅ | 0,16s |
| `mypy --strict` (pharmacy_os + seeds) | ✅ | ~7,1s |
| `pytest` | ❌ | **536s** — quá chậm cho từng commit |

**Hệ quả phải nói thẳng: hook KHÔNG chặn được commit làm đỏ pytest.** Trước khi đóng một
mục vẫn phải chạy đủ `make check` (~9 phút).

Đối chiếu với 3 ca commit-đỏ có thật trong lịch sử (audit C-02):

| Commit | Cổng đỏ | Hook có chặn được không? |
|---|---|:---:|
| `96ef714` | ruff (2 lỗi C408) | ✅ |
| `50ea91c` | ruff 24 lỗi + format 5 file | ✅ |
| `cd98f7b` | mypy 2 lỗi — **ca duy nhất chưa từng được tự khai** | ✅ |

Đó là lý do `mypy` nằm trong hook dù chậm hơn 3 cổng kia ~34 lần: ca mà con người kém nhất
trong việc tự bắt lại chính là ca chỉ `mypy` bắt được.

## Đường thoát

`git commit --no-verify` bỏ qua hook. Giữ lại có chủ đích — có lúc cần commit dở dang để
đóng phiên. Nhưng dùng nó là một **quyết định**: ghi vào `PROJECT_STATE.md` như mọi quyết
định tự chốt khác. Đi vòng qua kỷ luật #1 mà không để lại vết chính là thứ đã sinh ra phát
hiện **C-02**.
