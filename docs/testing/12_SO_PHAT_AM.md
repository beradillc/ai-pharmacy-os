# Sổ phát âm — sửa những chữ giọng đọc phát sai

> Chain 2026-08-02: *"Ghi nhận giọng này dùng mặc định trên hệ thống này của tôi, và kèm theo
> các góp ý để phát âm, cách đọc ngày càng học hỏi chuẩn tự nhiên dần."*
>
> **Giọng mặc định của hệ thống:** `vi_VN-vivos-x_low` · **spk62** — chốt 2026-08-02 sau khi
> quét 21 giọng nữ và chấm hai mặt (thanh điệu 1,18 · độ trong 0,64, cao nhất cả hai).
> Khai trong `scripts/doc_loi_thoai.py`; đổi giọng là đổi ở đó, không rải rác.

## Cách dùng sổ này

Nghe thấy chữ nào đọc sai → **thêm một dòng vào bảng "Đang sai"**. Không cần biết sửa thế nào;
ghi chữ đúng và chữ nghe thành là đủ. Lần dựng sau tôi tra phiên âm, tìm cách viết cho đúng
âm, rồi chuyển dòng đó xuống bảng "Đã sửa".

## 🔴 Trước tiên: có HAI loại lỗi, và chỉ một loại sửa được bằng chữ

Bộ đọc gồm hai tầng. **Tầng phiên âm** (espeak-ng) đổi chữ viết thành ký hiệu âm; **tầng giọng**
(mô hình Piper) đọc ký hiệu ấy thành tiếng. Tra phiên âm là biết lỗi nằm ở tầng nào:

| Loại | Dấu hiệu | Sửa được? |
|---|---|---|
| **Phiên âm sai** | Ký hiệu âm đã sai ngay từ đầu | ✅ Viết lại chữ cho ra đúng âm |
| **Giọng đọc bẹt** | Ký hiệu âm ĐÚNG, nhưng mô hình đọc không ra | ❌ Giới hạn của mô hình |

Tra bằng:

```
~/.local/share/beras-tts/venv/bin/python -c "
import ctypes; l=ctypes.CDLL('/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1')
l.espeak_Initialize(1,0,None,0); l.espeak_SetVoiceByName(b'vi')
l.espeak_TextToPhonemes.restype=ctypes.c_char_p
l.espeak_TextToPhonemes.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.c_int,ctypes.c_int]
b=ctypes.c_char_p('CHỮ CẦN TRA'.encode())
print(l.espeak_TextToPhonemes(ctypes.cast(ctypes.pointer(b),ctypes.POINTER(ctypes.c_void_p)),1,2).decode())"
```

## ✅ Đã sửa

| Chữ đúng | Chain nghe thành | Phiên âm cũ | Viết lại thành | Phiên âm mới |
|---|---|---|---|---|
| doanh | **dơn** | `zwˈe-ɲ` — nguyên âm `e`, sai | `doăn` | `zwˈan` — đúng `a`, và trùng cách miền Nam đọc vần "anh" |

## ❌ Chưa sửa được — giới hạn của mô hình, KHÔNG phải lỗi cách viết

Bốn chữ dưới đây **phiên âm đã đúng**. Viết lại kiểu gì cũng không đổi, vì lỗi nằm ở tầng giọng.

| Chữ | Chain nghe thành | Phiên âm (đúng) | Mô hình làm sai gì |
|---|---|---|---|
| tài khoản | tài **khoẻn** | `t̪ˈaː2j xwˈaː4n` | Nguyên âm `aː` sau `w` bị kéo ngắn lại |
| phần mềm | phần **mền** | `fˈə2n mˈe2m` | Phụ âm cuối `m` đọc yếu, nghe thành `n` |
| giả sử | giả **sư** | `zˈaː4 sˈy4` | Thanh hỏi (`4`) bị đọc bẹt thành ngang |
| lô | **lổ** | `lˈo` — không thanh | Mô hình **tự thêm** thanh hỏi vào chỗ không có |

**Ba trong bốn ca trên đều là chuyện THANH ĐIỆU** — đọc bẹt hoặc thêm thanh. Đó đúng là điểm
yếu của mô hình `x_low` (mức nhẹ nhất). Hai đường đi nếu Chain thấy không chấp nhận được:

1. **Đổi sang `vi_VN-vais1000-medium`** — mô hình nặng hơn, 22 kHz, thanh điệu đo được 0,91 và
   phụ âm cuối rõ hơn. Đổi lại: Chain đã nghe và nói **giọng miền Trung**. Tức là chọn giữa
   *đúng giọng* và *đúng chữ*.
2. **Thu giọng người** cho những video quan trọng nhất, giữ giọng máy cho phần còn lại.

## 📝 Đang sai — Chain ghi thêm vào đây

| Chữ đúng | Nghe thành | Ghi ngày |
|---|---|---|
| | | |

## Ghi chú

- Sổ này **không phải để mô hình tự học** — mô hình đã dựng xong, không học thêm được. Nó là
  bảng tra để tầng chữ viết bù cho chỗ tầng giọng làm chưa tới.
- Sửa một chữ ở đây thì **mọi video dựng sau đều đúng**, kể cả video đã quay từ trước, vì lời
  thoại được đọc lại từ bảng chứ không phải từ tệp âm thanh cũ.
