"""``demo_preview.py`` phải CHẠY ĐƯỢC, không chỉ lint sạch — audit A-08.

Tệp demo crash ngay dòng nối dây đầu tiên **suốt 5 ngày** (2026-07-23 → 07-28) vì hai
service mọc thêm tham số bắt buộc. F-1 đưa nó vào phạm vi ``ruff``/``mypy``, và điều đó
đúng nhưng **không đủ**: cả hai cổng đọc mã nguồn, không cổng nào gọi hàm. Một tệp
import sạch, gõ kiểu sạch, và nổ ở dòng đầu tiên là hoàn toàn nhất quán.

Test này chạy nó như người dùng chạy — tiến trình con, đúng lệnh ghi trong docstring của
chính tệp đó — và đòi mã thoát 0. Chạy trong tiến trình con chứ không ``import``: demo
tự dựng engine, tự ``asyncio.run``, và có ``sys.path.insert`` ở đầu; nhập nó vào tiến
trình test là kiểm một thứ khác với thứ người dùng chạy.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO = REPO_ROOT / "demo_preview.py"


def test_demo_preview_runs_to_completion() -> None:
    assert DEMO.is_file(), f"không tìm thấy {DEMO}"

    done = subprocess.run(  # noqa: S603
        [sys.executable, str(DEMO)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert done.returncode == 0, (
        f"demo_preview.py thoát {done.returncode} — đúng lỗi A-08 tái phát.\n"
        f"stdout:\n{done.stdout[-2000:]}\nstderr:\n{done.stderr[-2000:]}"
    )


def test_demo_preview_does_not_claim_other_modules_are_unimplemented() -> None:
    """Bản cũ tuyên bố Sales/POS và Clinical *"CHƯA hiện thực"* trong khi cả hai đã
    chạy thật. Một tệp demo nói sai về hệ thống là cùng loại lỗi với A-06/B-06 — văn
    bản phát ra khẳng định mà mã nguồn không còn đúng."""
    text = DEMO.read_text(encoding="utf-8")

    assert "Sales/POS (Sprint 4) và Clinical/Prescription (Sprint 5) CHƯA hiện thực" not in text
