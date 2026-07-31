"""Location domain exceptions (pure — no framework)."""

from __future__ import annotations


class LocationError(Exception):
    """Base for location domain rule violations."""


class InvalidLocationCodeError(LocationError):
    """Mã vị trí rỗng, quá dài, hoặc chứa ký tự không dùng được trong đường dẫn."""


class InvalidLocationNestingError(LocationError):
    """Lồng sai thứ bậc — ví dụ đặt một Khu bên trong một Ô.

    Thứ bậc là ràng buộc **thứ tự**, không phải ràng buộc **đủ tầng**: một nhà thuốc nhỏ
    có thể chỉ dùng Kho → Kệ, bỏ qua Khu và Ô. Bỏ tầng thì được; đảo tầng thì không.
    """


class DuplicateLocationCodeError(LocationError):
    """Trùng mã trong cùng một cha.

    Trùng ở hai cha khác nhau là **hợp lệ và cần thiết**: ô "01" dưới kệ A và ô "01" dưới
    kệ B là hai chỗ khác nhau, và bắt nhà thuốc đặt mã duy nhất toàn kho là bắt họ bỏ đúng
    cách đánh số mà họ đang dán trên kệ.
    """


class LocationHasChildrenError(LocationError):
    """Không ngừng hoạt động một vị trí còn vị trí con đang hoạt động.

    Ngừng cha mà để con lại sẽ tạo ra những ô vẫn nhận hàng được nhưng nằm dưới một kệ đã
    khai tử — trạng thái không ai đọc ra được từ màn hình.
    """
