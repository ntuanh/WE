"""In log mà không bao giờ làm chết app.

Console của Windows mặc định là cp1252, không mã hoá nổi chữ tiếng Việt có dấu
hay mũi tên "→". Một câu print lúc khởi động mà nổ UnicodeEncodeError là cả app
không import được — lỗi khó đoán vì thủ phạm chỉ là một dòng log.
"""

import sys


def log(message: str) -> None:
    """In ra stdout, tự thay ký tự nào console không hiển thị được."""
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(message.encode(encoding, "replace").decode(encoding, "replace"))
    except Exception:
        pass  # log hỏng thì thôi, tuyệt đối không được làm chết app
