import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";

/** Cạnh dài tối đa sau khi thu nhỏ. 1600px đủ đọc chữ viết tay trên đơn A5. */
const CANH_DAI_MAX = 1600;

/** Chất lượng JPEG. 0,7 là chỗ ảnh còn đọc được mà kích thước đã giảm khoảng một bậc. */
const CHAT_LUONG = 0.7;

/**
 * Thu nhỏ ảnh **trong trình duyệt** rồi trả về base64 (không kèm tiền tố `data:`).
 *
 * 🔴 Vì sao phải nén ở đây chứ không gửi thẳng ảnh gốc: ảnh điện thoại thô là 2–5 MB, qua
 * base64 → mã hoá at-rest → base64 lần nữa thành **3,6–9 MB một dòng CSDL**. Với vài chục
 * đơn ETC mỗi ngày, `pg_dump` chậm tới mức người ta thôi chạy nó — và mất backup tệ hơn
 * nhiều so với mất một tấm ảnh.
 *
 * Đây là **tiện lợi, không phải cổng**: máy chủ vẫn đo lại kích thước sau khi giải mã và
 * từ chối quá 2 MB. Một máy khách khác, hoặc chính máy khách này bị sửa, không đi vòng
 * được qua giới hạn ấy.
 */
export async function nenAnh(file: File): Promise<{ data: string; contentType: string }> {
  const bitmap = await createImageBitmap(file);
  const tiLe = Math.min(1, CANH_DAI_MAX / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * tiLe);
  canvas.height = Math.round(bitmap.height * tiLe);

  const ctx = canvas.getContext("2d");
  if (ctx === null) throw new Error("Trình duyệt không cho vẽ ảnh để nén");
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();

  // `toDataURL` trả `data:image/jpeg;base64,XXXX` — máy chủ chỉ nhận phần XXXX. Gửi cả
  // tiền tố lên sẽ làm base64 hỏng ở phía máy chủ và lỗi hiện ra dưới dạng "ảnh không
  // hợp lệ", một thông điệp không chỉ được về đây.
  const dataUrl = canvas.toDataURL("image/jpeg", CHAT_LUONG);
  return { data: dataUrl.split(",")[1] ?? "", contentType: "image/jpeg" };
}

export interface RxPhotoInput {
  customerId: string;
  doctorName: string;
  lines: { drugId: string; quantity: string }[];
  file: File;
}

/**
 * Chụp đơn ở quầy: tạo đơn thuốc **từ ảnh** rồi gắn ảnh vào, hai lượt gọi.
 *
 * `source: "IMAGE"` là thứ cho phép để trống liều/tần suất/thời gian — người đứng quầy
 * không biết chúng, chúng chỉ có trên tờ giấy. Mã thuốc và số lượng thì lấy từ giỏ nên là
 * **thật**; ba ô kia để rỗng nghĩa là *"chưa phiên từ ảnh"*, không phải một con số bịa.
 *
 * Hai lượt chứ không một: `POST /prescriptions` là đường tạo đơn đã có từ trước và không
 * nhận ảnh; ghép ảnh vào đó sẽ phải sửa một hợp đồng API đang chạy. Nếu lượt thứ hai hỏng,
 * đơn vẫn tồn tại không có ảnh — dược sĩ chụp lại được, và `PUT` là idempotent.
 */
export function useRxPhoto() {
  return useMutation({
    mutationFn: async ({ customerId, doctorName, lines, file }: RxPhotoInput) => {
      const { data, contentType } = await nenAnh(file);
      const rx = await apiFetch<{ id: string }>("/prescriptions", {
        method: "POST",
        body: {
          customer_id: customerId,
          doctor_name: doctorName,
          source: "IMAGE",
          items: lines.map((l) => ({
            drug_id: l.drugId,
            quantity: l.quantity,
            dose: "",
            frequency: "",
            duration: "",
          })),
        },
      });
      await apiFetch(`/prescriptions/${rx.id}/image`, {
        method: "PUT",
        body: { image_data: data, content_type: contentType },
      });
      return rx.id;
    },
  });
}
