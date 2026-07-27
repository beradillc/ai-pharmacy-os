"""F-17 — đo p95 đường POS trên staging. DoD Sprint 8: p95 < 300 ms.

    python scripts/load_test_pos.py [ĐỒNG_THỜI] [SỐ_REQUEST]      # mặc định 8 400

⚠️ **Một con số p95 không kèm mức tải là một con số vô nghĩa.** Đo thật 2026-07-28 cho
thấy cùng hệ thống này ĐẠT ở 8 luồng (217,6 ms) và KHÔNG ĐẠT ở 16 luồng (490,4 ms).
Ai trích lại "p95 = 217 ms" mà bỏ mức tải là đang trích một nửa sự thật.

Đo cái gì: **đường mà thu ngân thật sự đi trong một lần bán** — tra thuốc → tạo đơn.
Không đo `/health` (không chạm CSDL, con số đẹp mà vô nghĩa).

Không đo `/auth/login`: F-9 giới hạn 10 lượt/phút mỗi IP, nên bắn tải vào đó chỉ đo
được chính cái rate limiter. Đăng nhập một lần, dùng lại token — đúng như POS thật.
"""

import asyncio
import statistics
import sys
import time

import httpx

BASE = "http://localhost:8001/api/v1"
EMAIL, PASSWORD = "admin@staging.local", "MatKhauStaging2026x"
CONCURRENCY = int(sys.argv[1]) if len(sys.argv) > 1 else 8
TOTAL = int(sys.argv[2]) if len(sys.argv) > 2 else 400


async def main() -> int:
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        r.raise_for_status()
        hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # Dựng danh mục tối thiểu cho đường bán: 1 thuốc + tồn kho.
        drug = await c.post(
            f"{BASE}/drugs",
            headers=hdr,
            json={
                "name": f"Thuoc do tai F17 {int(time.time())}",
                "rx_class": "OTC",
                "base_unit": "vien",
            },
        )
        drug.raise_for_status()
        drug_id = drug.json()["id"]
        rec = await c.post(
            f"{BASE}/inventory/receive",
            headers=hdr,
            json={
                "drug_id": drug_id,
                "lot_no": "F17-LOT",
                "expiry_date": "2027-12-31",
                "quantity": "1000000",
                "cost_price": "1000",
            },
        )
        rec.raise_for_status()

        scenarios = {
            "GET /drugs (tra thuốc)": lambda: c.get(f"{BASE}/drugs?limit=20", headers=hdr),
            "GET /inventory/on-hand": lambda: c.get(
                f"{BASE}/inventory/on-hand?drug_id={drug_id}", headers=hdr
            ),
            "POST /sales (chốt đơn)": lambda: c.post(
                f"{BASE}/sales",
                headers=hdr,
                json={
                    "client_uuid": str(__import__("uuid").uuid4()),
                    "lines": [
                        {
                            "drug_id": drug_id,
                            "quantity": "1",
                            "unit_price": "5000",
                            "requires_prescription": False,
                        }
                    ],
                    "payments": [{"method": "CASH", "amount": "5000"}],
                },
            ),
        }

        print(f"đồng thời={CONCURRENCY} · mỗi kịch bản {TOTAL} request\n")
        print(
            f"{'kịch bản':28s} {'n':>5s} {'lỗi':>4s} {'p50':>8s} "
            f"{'p95':>8s} {'p99':>8s} {'max':>8s}"
        )
        worst_p95 = 0.0
        for name, call in scenarios.items():
            sem = asyncio.Semaphore(CONCURRENCY)
            lat: list[float] = []
            errs = 0

            # Buộc theo tham số, không theo biến vòng lặp (ruff B023): ở đây vô hại
            # vì mỗi vòng await xong mới sang vòng sau, nhưng đó là loại lỗi chỉ lộ
            # ra khi ai đó bỏ await — chặn từ đầu rẻ hơn nhiều.
            async def one(call=call, lat=lat, sem=sem) -> None:
                nonlocal errs
                async with sem:
                    t = time.perf_counter()
                    try:
                        resp = await call()
                        d = (time.perf_counter() - t) * 1000
                        if resp.status_code >= 400:
                            errs += 1
                        else:
                            lat.append(d)
                    except Exception:
                        errs += 1

            await asyncio.gather(*(one() for _ in range(20)))  # khởi động, bỏ số
            lat.clear()
            errs = 0
            await asyncio.gather(*(one() for _ in range(TOTAL)))
            if not lat:
                print(f"{name:28s} {0:5d} {errs:4d}   (không request nào thành công)")
                continue
            q = statistics.quantiles(lat, n=100)
            p50, p95, p99 = q[49], q[94], q[98]
            worst_p95 = max(worst_p95, p95)
            print(
                f"{name:28s} {len(lat):5d} {errs:4d} {p50:7.1f}m "
                f"{p95:7.1f}m {p99:7.1f}m {max(lat):7.1f}m"
            )
        print(
            f"\np95 xấu nhất = {worst_p95:.1f} ms · ngưỡng DoD = 300 ms · "
            f"{'ĐẠT' if worst_p95 < 300 else 'KHÔNG ĐẠT'}"
        )
        return 0 if worst_p95 < 300 else 1


sys.exit(asyncio.run(main()))
