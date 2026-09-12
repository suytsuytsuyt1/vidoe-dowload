# -*- coding: utf-8 -*-
"""
GIAO DIỆN CỬA SỔ (tkinter) CHO "VIDEO DOWNLOADER"
Hỗ trợ 2 GIAO DIỆN đổi qua lại được (nút 🌙/☀ trên banner): Sáng (tối giản, nền
trắng) và Tối (nền tối, nút hành động chính tô xanh dương). Lựa chọn được ghi
nhớ vào file "cai_dat_giao_dien.json" cạnh chương trình cho lần mở sau.

CÁCH DÙNG:
    python tai_video_gui.py

YÊU CẦU: file tai_video_core.py phải nằm CÙNG THƯ MỤC với file này.

TỰ ĐỘNG CÀI THÊM: chương trình tự cài các thư viện pip còn thiếu khi khởi động
(psutil, plugin PO Token) và tự cài yt-dlp qua pip nếu không tìm thấy trên máy -
không cần người dùng tự gõ lệnh "pip install ...". Riêng PYTHON thì KHÔNG tự cài
được (file .py này cần Python đã có sẵn trên máy thì mới chạy được để tự cài mấy
thứ kia). Giao diện chỉ dùng thư viện chuẩn của Python (tkinter) - không cần
Pillow hay bất kỳ gói vẽ ảnh nào, để giảm rủi ro lỗi cài đặt (logo dùng ảnh PNG
có sẵn trong assets/, tkinter tự đọc được PNG từ Tk 8.6 trở lên, không cần Pillow).
Cookie đăng nhập YouTube (khi cần) lấy qua Extension Chrome tự viết + Native
Messaging - xem extension_cookie.py - KHÔNG cần cài thêm thư viện pip nào cho
việc này (đã bỏ hẳn cách cũ dùng Playwright/Chrome DevTools Protocol).
"""

import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

import tai_video_core as core
import thumbnail_core as thumb_core
import extension_cookie
# Cookie dùng để tải video giờ đi qua ĐÚNG yt-dlp (qua _chay_1_tien_trinh_video),
# kèm cờ --cookies - y hệt cách các lượt tải không-cookie vẫn làm, chỉ khác là có
# thêm cờ cookie. Đường "tự gọi Innertube API, không qua yt-dlp" (module rời
# tai_khong_ytdlp.py) đã bị bỏ hẳn và xoá khỏi đĩa vì SAI KIẾN TRÚC từ đầu (PO
# Token sinh bởi bgutil-pot kiểu BotGuard/web KHÔNG dùng được cho client
# ANDROID/IOS trần - cần droidguard/iosguard, cơ chế điểm danh thiết bị thật khác
# hẳn BotGuard) - tái dùng hạ tầng PO Token/client-version do đội yt-dlp bảo trì
# liên tục là cách ổn định duy nhất.

# Số luồng tải song song CỐ ĐỊNH cho cả tab Video lẫn tab Thumbnails (không cho người
# dùng tự chỉnh nữa - mức 5 là điểm cân bằng an toàn giữa tốc độ và rủi ro bị YouTube
# để ý/giới hạn tốc độ khi tải quá nhiều luồng cùng lúc).
SO_LUONG_CO_DINH = core.SO_LUONG_SONG_SONG_MAC_DINH

TEN_CHUONG_TRINH = "Video Downloader"


def an_cua_so_cmd_neu_an_toan():
    """Ẩn cửa sổ CMD đen chạy kèm khi khởi động bằng "python" (thay vì "pythonw"),
    hoặc khi đóng gói .exe mà quên bật --windowed.
    CHỈ ẨN khi cửa sổ console đó là CỦA RIÊNG chương trình này (do Windows tự tạo
    ra cho tiến trình python.exe) - KHÔNG ẨN nếu người dùng tự mở sẵn 1 cửa sổ CMD
    của họ rồi gõ lệnh "python tai_video_gui.py" trong đó, vì lúc đó cửa sổ CMD là
    CỦA NGƯỜI DÙNG (dùng chung với các chương trình khác) - ẩn nhầm sẽ làm cả cửa
    sổ CMD của họ biến mất, tưởng nhầm là máy bị lỗi."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        cua_so_console = kernel32.GetConsoleWindow()
        if not cua_so_console:
            return  # không có console nào cả (VD chạy bằng pythonw) -> không cần làm gì

        # Đếm xem có bao nhiêu tiến trình đang "sở hữu chung" cửa sổ console này.
        # Nếu chỉ có DUY NHẤT 1 tiến trình (chính chương trình này) -> chắc chắn là
        # console Windows tự tạo riêng cho nó -> an toàn để ẩn.
        # Nếu có từ 2 tiến trình trở lên -> đây là cửa sổ CMD người dùng đang dùng
        # chung (VD họ tự mở cmd.exe rồi gõ lệnh chạy) -> KHÔNG ẩn.
        danh_sach_pid = (ctypes.c_uint * 4)()
        so_luong = kernel32.GetConsoleProcessList(danh_sach_pid, 4)
        if so_luong <= 1:
            SW_HIDE = 0
            ctypes.windll.user32.ShowWindow(cua_so_console, SW_HIDE)
    except Exception:
        pass


def duong_dan_tai_nguyen(ten_file):
    """Trả về đường dẫn tới file tài nguyên (icon...).
    Hoạt động cả khi chạy bằng python thường lẫn khi đã đóng gói .exe bằng PyInstaller
    (PyInstaller giải nén tài nguyên vào thư mục tạm sys._MEIPASS lúc chạy)."""
    if hasattr(sys, "_MEIPASS"):
        thu_muc_goc = sys._MEIPASS
    else:
        thu_muc_goc = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(thu_muc_goc, "assets", ten_file)

# ================== HỆ THỐNG 2 GIAO DIỆN (SÁNG / TỐI) ==================
# Chương trình hỗ trợ 2 "bộ giao diện" người dùng có thể tự đổi qua lại bằng nút
# 🌙/☀ trên banner (xem _doi_giao_dien): "sang" (tối giản, nền trắng - phong cách
# cũ) và "toi" (nền tối, nút chính tô màu xanh dương làm điểm nhấn). Mọi widget
# trong chương trình đọc màu qua các biến MAU_*/FONT_* Ở CẤP MODULE bên dưới -
# khi đổi giao diện, các biến này được gán lại (xem ap_dung_bang_mau) rồi TOÀN BỘ
# khung nội dung được dựng lại từ đầu để mọi widget mới tạo ra đọc đúng bộ màu mới,
# thay vì phải dò từng widget cũ để tô lại (dễ sót, dễ lệch màu).
#
# QUY TẮC TỶ LỆ: mọi kích thước trong 2 giao diện đều dùng cùng 1 hệ font/khoảng
# cách/co giãn theo cửa sổ (xem GIOI_HAN_CHIEU_CAO_VUNG_CUON, CHIEU_CAO_NOTEBOOK,
# và cách bố trí bằng grid/pack với weight co giãn) - đổi giao diện KHÔNG đổi bố
# cục hay kích thước, chỉ đổi màu sắc/điểm nhấn, nên khi kéo giãn cửa sổ ở bất kỳ
# giao diện nào cũng giữ được tỷ lệ hài hoà y hệt nhau.

BANG_MAU_SANG = {
    "MAU_NEN": "#F5F6F8",
    "MAU_THE": "#FFFFFF",
    "MAU_VIEN": "#E2E4E9",
    "MAU_CHU_CHINH": "#1E2328",
    "MAU_CHU_PHU": "#6C7178",
    "MAU_NHAN": "#1E2328",
    "MAU_NHAN_HOVER": "#3A3F45",
    "MAU_NUT_CHINH_BG": "#FFFFFF",
    "MAU_NUT_CHINH_BG_HOVER": "#EEF0F3",
    "MAU_NUT_CHINH_CHU": "#1E2328",
    "MAU_VIEN_NUT_CHINH": "#1E2328",
    "MAU_CHU_NUT_CANH_BAO": "#000000",
    "MAU_CHU_VO_HIEU": "#B8B8B0",
    "MAU_THANH_CONG": "#3E8F76",
    "MAU_LOI": "#B5564C",
    "MAU_CANH_BAO_BG": "#FFFFFF",
    "MAU_CANH_BAO_BG_HOVER": "#EEF0F3",
    "MAU_VIEN_CANH_BAO": "#6C7178",
    "MAU_PHU_NHAT": "#EEF0F3",
    "MAU_DIEM_TRANG_THAI_SAN_SANG": "#9CA1A8",
    "MAU_DIEM_TRANG_THAI_DANG_CHAY": "#3E8F76",
    "MAU_DIEM_TRANG_THAI_LOI": "#B5564C",
    "MAU_LOGO_NEN": "#FFFFFF",
    "MAU_LOGO_VIEN": "#1E2328",
}

# Giao diện TỐI: lấy cảm hứng từ khung nổi màu tối (nền xanh than đậm, thẻ/khung
# xám-xanh đậm hơn 1 chút, viền mảnh, chữ trắng ngà) và nút hành động chính tô hẳn
# màu xanh dương làm điểm nhấn - khác nút chính "chỉ viền" của giao diện sáng.
BANG_MAU_TOI = {
    "MAU_NEN": "#15171D",
    "MAU_THE": "#20232C",
    "MAU_VIEN": "#343A47",
    "MAU_CHU_CHINH": "#EDEFF3",
    "MAU_CHU_PHU": "#9AA0AC",
    "MAU_NHAN": "#5B9DFF",
    "MAU_NHAN_HOVER": "#7CB0FF",
    "MAU_NUT_CHINH_BG": "#3D7EFF",
    "MAU_NUT_CHINH_BG_HOVER": "#5C90FF",
    "MAU_NUT_CHINH_CHU": "#FFFFFF",
    "MAU_VIEN_NUT_CHINH": "#3D7EFF",
    "MAU_CHU_NUT_CANH_BAO": "#EDEFF3",
    "MAU_CHU_VO_HIEU": "#5A5F6B",
    "MAU_THANH_CONG": "#4CD08A",
    "MAU_LOI": "#FF7A7A",
    "MAU_CANH_BAO_BG": "#20232C",
    "MAU_CANH_BAO_BG_HOVER": "#2B303C",
    "MAU_VIEN_CANH_BAO": "#454B59",
    "MAU_PHU_NHAT": "#2B303C",
    "MAU_DIEM_TRANG_THAI_SAN_SANG": "#6B7280",
    "MAU_DIEM_TRANG_THAI_DANG_CHAY": "#4CD08A",
    "MAU_DIEM_TRANG_THAI_LOI": "#FF7A7A",
    "MAU_LOGO_NEN": "#3D7EFF",
    "MAU_LOGO_VIEN": "#3D7EFF",
}

GIAO_DIEN_MAC_DINH = "sang"
_giao_dien_hien_tai = GIAO_DIEN_MAC_DINH


def ap_dung_bang_mau(ten_giao_dien):
    """Gán lại TOÀN BỘ biến màu MAU_* ở cấp module theo đúng bộ giao diện được chọn
    ('sang' hoặc 'toi'). Gọi hàm này XONG rồi phải dựng lại giao diện (xem
    _doi_giao_dien) thì các widget MỚI mới đọc được màu mới - các widget CŨ đã
    tạo ra từ trước sẽ không tự đổi màu (vì tkinter đọc màu ngay lúc tạo widget)."""
    global _giao_dien_hien_tai
    bang = BANG_MAU_TOI if ten_giao_dien == "toi" else BANG_MAU_SANG
    globals().update(bang)
    _giao_dien_hien_tai = "toi" if ten_giao_dien == "toi" else "sang"


def duong_dan_file_cai_dat():
    """File nhỏ lưu lựa chọn giao diện (sáng/tối) giữa các lần mở chương trình,
    đặt CẠNH file chương trình (hoặc cạnh file .exe khi đã đóng gói) để dễ tìm/xoá."""
    if hasattr(sys, "_MEIPASS"):
        thu_muc = os.path.dirname(os.path.abspath(sys.executable))
    else:
        thu_muc = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(thu_muc, "cai_dat_giao_dien.json")


def doc_giao_dien_da_luu():
    """Đọc lựa chọn giao diện lần trước, mặc định 'sang' nếu chưa có/lỗi file."""
    try:
        with open(duong_dan_file_cai_dat(), "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
        ten = du_lieu.get("giao_dien")
        return "toi" if ten == "toi" else "sang"
    except Exception:
        return GIAO_DIEN_MAC_DINH


def luu_giao_dien(ten_giao_dien):
    """Lưu lựa chọn giao diện ra file. Lỗi ghi file (VD thư mục chỉ đọc) sẽ bị bỏ
    qua ÂM THẦM - đây chỉ là tiện ích ghi nhớ, không phải chức năng bắt buộc, không
    đáng để làm phiền người dùng bằng hộp thoại lỗi."""
    try:
        with open(duong_dan_file_cai_dat(), "w", encoding="utf-8") as tep:
            json.dump({"giao_dien": ten_giao_dien}, tep)
    except Exception:
        pass


# Khởi tạo bộ màu ban đầu theo lựa chọn đã lưu (nếu có) TRƯỚC khi bất kỳ class nào
# bên dưới đọc các biến MAU_* làm giá trị mặc định.
ap_dung_bang_mau(doc_giao_dien_da_luu())

FONT_THUONG = ("Segoe UI", 10)
FONT_NHAN = ("Segoe UI", 9)
FONT_TIEU_DE = ("Segoe UI", 16, "bold")
FONT_PHU_DE = ("Segoe UI", 10)
FONT_TIEU_DE_MUC = ("Segoe UI", 10, "bold")
FONT_NUT = ("Segoe UI", 10)
FONT_NUT_CHINH = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas", 9)

# Chiều cao tối đa (px) của vùng cuộn cấu hình trong MỖI tab. Cố định (không phụ
# thuộc kích thước cửa sổ) để tổng chiều cao mọi thành phần luôn dự đoán được,
# đảm bảo khung "Thông tin" phía dưới luôn có chỗ hiển thị ngay từ đầu.
GIOI_HAN_CHIEU_CAO_VUNG_CUON = 250
# Chiều cao cố định của khối Notebook (thanh tab + toàn bộ 1 tab, gồm cả vùng cuộn
# lẫn hàng nút bấm cố định bên dưới nó) - đủ chỗ cho tab dài nhất (Thumbnails).
CHIEU_CAO_NOTEBOOK = 390


class NutTrangTron(tk.Button):
    """Nút phụ: nền trắng, viền mỏng, chữ đen. Có hiệu ứng đổi màu nhẹ khi rê chuột qua
    (hover) để nhìn "sống" hơn, và tự chuyển màu xám khi bị vô hiệu hoá (disabled)."""
    def __init__(self, cha, **kwargs):
        super().__init__(
            cha,
            bg=MAU_THE, fg=MAU_CHU_CHINH,
            activebackground=MAU_PHU_NHAT, activeforeground=MAU_CHU_CHINH,
            disabledforeground=MAU_CHU_VO_HIEU,
            font=FONT_NUT, relief="solid", bd=1,
            highlightbackground=MAU_VIEN, highlightthickness=1,
            padx=14, pady=8, cursor="hand2",
            **kwargs,
        )
        self.bind("<Enter>", self._khi_chuot_vao)
        self.bind("<Leave>", self._khi_chuot_ra)

    def _khi_chuot_vao(self, _event):
        if self["state"] != "disabled":
            self.configure(bg=MAU_PHU_NHAT)

    def _khi_chuot_ra(self, _event):
        if self["state"] != "disabled":
            self.configure(bg=MAU_THE)


class NutDen(tk.Button):
    """Nút chính: nền TRẮNG (như mọi thứ khác), chỉ nổi bật hơn nút phụ nhờ VIỀN ĐẬM
    (2px, màu đen-xám) và CHỮ MÀU ĐEN THẬT SỰ (không dùng xám/xám đậm) để dễ đọc nhất
    có thể - CHỦ Ý không tô màu nền để đỡ chói mắt."""
    def __init__(self, cha, **kwargs):
        super().__init__(
            cha,
            bg=MAU_NUT_CHINH_BG, fg=MAU_NUT_CHINH_CHU,
            activebackground=MAU_NUT_CHINH_BG_HOVER, activeforeground=MAU_NUT_CHINH_CHU,
            font=FONT_NUT_CHINH, relief="solid", bd=2,
            highlightbackground=MAU_VIEN_NUT_CHINH, highlightthickness=0,
            padx=16, pady=8, cursor="hand2",
            disabledforeground=MAU_CHU_VO_HIEU,
            **kwargs,
        )
        self._mau_binh_thuong = MAU_NUT_CHINH_BG
        self.bind("<Enter>", self._khi_chuot_vao)
        self.bind("<Leave>", self._khi_chuot_ra)

    def _khi_chuot_vao(self, _event):
        if self["state"] != "disabled":
            self.configure(bg=MAU_NUT_CHINH_BG_HOVER)

    def _khi_chuot_ra(self, _event):
        if self["state"] != "disabled":
            self.configure(bg=self._mau_binh_thuong)


class NutCanhBao(tk.Button):
    """Nút cảnh báo (dùng cho '⏸ Tạm dừng' / '✕ Huỷ' lúc đang tải) - CŨNG nền trắng
    như nút chính, CHỮ MÀU ĐEN THẬT SỰ (trước đây dùng chữ xám nên khó đọc) để dễ nhìn
    nhất, chỉ khác nút chính ở viền mỏng hơn (1px thay vì 2px) để vẫn phân biệt được
    đây là hành động 'dừng việc đang chạy' chứ không phải hành động bắt đầu mới."""
    def __init__(self, cha, **kwargs):
        super().__init__(
            cha,
            bg=MAU_CANH_BAO_BG, fg=MAU_CHU_NUT_CANH_BAO,
            activebackground=MAU_CANH_BAO_BG_HOVER, activeforeground=MAU_CHU_NUT_CANH_BAO,
            font=FONT_NUT, relief="solid", bd=1,
            highlightbackground=MAU_VIEN_CANH_BAO, highlightthickness=0,
            padx=14, pady=8, cursor="hand2",
            disabledforeground=MAU_CHU_VO_HIEU,
            **kwargs,
        )
        self.bind("<Enter>", self._khi_chuot_vao)
        self.bind("<Leave>", self._khi_chuot_ra)

    def _khi_chuot_vao(self, _event):
        if self["state"] != "disabled":
            self.configure(bg=MAU_CANH_BAO_BG_HOVER)

    def _khi_chuot_ra(self, _event):
        if self["state"] != "disabled":
            self.configure(bg=MAU_CANH_BAO_BG)


class UngDungTaiVideo:
    def __init__(self, cua_so_goc):
        self.cua_so_goc = cua_so_goc
        cua_so_goc.title(TEN_CHUONG_TRINH)
        cua_so_goc.configure(bg=MAU_NEN)
        cua_so_goc.option_add("*Font", FONT_THUONG)
        self._ap_dung_style_ttk()
        self._dat_kich_thuoc_cua_so_theo_man_hinh()
        cua_so_goc.resizable(True, True)  # cho phép co giãn/kéo lớn nhỏ cửa sổ tùy ý
        self._dat_icon_cua_so()

        self.tong_so_video = None
        self.danh_sach_thieu = []
        self.do_rong_dem = 3

        # Trạng thái bước "1) Đếm & quét file đã tải" của tab Thumbnails - cùng cơ
        # chế đếm/quét-file-đã-có với tab "Tải video" ở trên, nhưng lưu THẲNG danh
        # sách (stt, video) còn thiếu (không chỉ mỗi số STT) vì bước tải thumbnail
        # cần thông tin video (id, tiêu đề) lấy sẵn từ API, không dò lại qua yt-dlp
        # bằng URL kênh như bên tải video.
        self.tong_so_video_thumb = None
        self.danh_sach_thieu_thumb = []
        self.thu_muc_luu_thumb_da_chon = None

        # Trạng thái theo dõi tiến độ tải ngầm (không dùng cửa sổ CMD rời nữa)
        self._khoa_tien_do = threading.Lock()
        self._so_video_can_tai_dot_nay = 0
        self._so_video_da_xong_dot_nay = 0
        self._so_tien_trinh_dang_chay = 0   # số LUỒNG (thread) tải đang chạy, mỗi luồng
                                             # tự lặp tải từng video một (không phải số
                                             # tiến trình yt-dlp, vì mỗi luồng tạo NHIỀU
                                             # tiến trình yt-dlp lần lượt, mỗi video 1 cái)
        self._tien_trinh_hien_tai_theo_luong = {}  # idx_luong -> Popen ĐANG chạy (nếu có),
                                                    # dùng để Tạm dừng có thể kill đúng
                                                    # tiến trình đang tải dở của từng luồng
        self._dang_tam_dung = False
        # "Số thế hệ" của đợt khởi động tiến trình hiện tại - tăng lên mỗi lần
        # _khoi_dong_cac_tien_trinh được gọi (kể cả lúc bấm 'Tiếp tục' sau Tạm dừng).
        # Dùng để CÁC LUỒNG ĐỌC LOG CŨ (từ tiến trình vừa bị kill lúc Tạm dừng) tự
        # nhận ra mình đã "lỗi thời" nếu báo cáo về TRỄ sau khi người dùng đã bấm
        # 'Tiếp tục' quá nhanh - tránh trừ nhầm vào bộ đếm của đợt tải MỚI (race
        # condition: tiến trình cũ chưa kịp đóng hẳn ống stdout thì đợt mới đã bắt đầu).
        self._the_he_tai_dot_nay = 0
        self._thong_tin_dot_tai = {}                  # url/shorts/thư mục/chất lượng của đợt tải hiện tại
        self._danh_sach_stt_theo_luong_dot_nay = []    # cách chia luồng (list số STT), dùng khi Tiếp tục

        # Trạng thái "dò cookie" DÙNG CHUNG CHO CẢ PHIÊN CHẠY APP (không dò lại mỗi
        # video) - None: chưa dò lần nào; "khong_co": đã dò mà không lấy được cookie
        # dùng được (Extension chưa thiết lập/chưa gửi cookie, hoặc có cookie nhưng
        # yt-dlp vẫn báo lỗi); hoặc tuple ("file", duong_dan_file_cookie) nếu Extension
        # đã gửi sẵn cookie hợp lệ (xem extension_cookie.py) - tuple này được dùng
        # THẲNG làm nguon_cookie khi gọi core.xay_dung_lenh(), không cần chuyển đổi
        # gì thêm. Xem _lay_nguon_cookie_de_dung().
        self._khoa_cookie = threading.Lock()
        self._nguon_cookie_hoat_dong = None

        # (Đã BỎ cache danh sách video kênh qua YouTube Data API dùng riêng cho
        # đường tải "không qua yt-dlp" - đường đó không còn tồn tại nữa, xem comment
        # dài ở đầu file cạnh "import tai_khong_ytdlp" cũ. _tai_1_video_bang_cookie_khong_ytdlp
        # giờ gọi thẳng yt-dlp như bình thường nên không cần tự dò video theo STT
        # qua API riêng nữa - yt-dlp tự làm việc đó qua --playlist-items.)


        # Ghi lại TOÀN BỘ log của lần chạy này ra 1 file .txt riêng (yêu cầu người
        # dùng - trước đây log chỉ nằm trong khung chữ trên giao diện, mất hẳn khi
        # đóng app, không xem lại được). Mỗi lần MỞ app -> 1 file mới (tên kèm ngày
        # giờ) - xem core.chuan_bi_file_log_moi(): tự dọn bớt file CŨ NHẤT nếu đã có
        # từ 10 LẦN CHẠY GẦN NHẤT trở lên, để không tích file vô hạn theo thời gian
        # (giữ đúng 10 lần chạy gần nhất, kể cả lần đang mở này). Ghi file ngay tại
        # dòng gọi _ghi_log() (không đợi qua luồng chính tkinter như phần hiện lên
        # khung chữ) để không mất dòng nào kể cả khi cửa sổ bị đóng đột ngột giữa
        # chừng; _khoa_file_log đảm bảo nhiều luồng tải cùng ghi log 1 lúc không bị
        # chồng/lẫn dòng vào nhau. self._duong_dan_file_log = None nghĩa là tính
        # năng ghi file bị tắt cho lần chạy này (lỗi khi chuẩn bị file, VD không đủ
        # quyền ghi vào thư mục AppData) - _ghi_log tự bỏ qua phần ghi file, KHÔNG
        # được để ảnh hưởng tới phần hiện log lên giao diện (tính năng chính).
        self._khoa_file_log = threading.Lock()
        self._duong_dan_file_log = core.chuan_bi_file_log_moi()

        # Trạng thái riêng cho tab Thumbnails
        self._huy_tai_thumbnail = False
        self._dang_tai_thumbnail = False

        self._xay_dung_giao_dien()

        if self._duong_dan_file_log:
            self._ghi_log(f"📝 Log của lần chạy này đang được lưu vào: {self._duong_dan_file_log}")
        else:
            self._ghi_log("⚠ Không tạo được file log cho lần chạy này (không ảnh hưởng tới "
                          "việc tải video) - log sẽ chỉ hiện trên màn hình như trước, không lưu "
                          "lại được.", mau=MAU_LOI)

        # BẮT sự kiện bấm nút X đóng cửa sổ, để ĐẢM BẢO dừng hẳn mọi tiến trình
        # yt-dlp/ffmpeg đang chạy ngầm trước khi thoát - xem chi tiết ở hàm
        # _khi_dong_cua_so bên dưới.
        self.cua_so_goc.protocol("WM_DELETE_WINDOW", self._khi_dong_cua_so)

        # KHOÁ toàn bộ ứng dụng (hiện màn hình "Đang chuẩn bị...") NGAY LÚC MỞ, trước
        # khi các bước tự động dò/tải công cụ (yt-dlp, ffmpeg, ffprobe, PO Token, thư
        # viện Thumbnails) chạy xong - người dùng không bấm được gì trong lúc này, tự
        # mở khoá ngay khi chay_nen() ở dưới hoàn tất (xem _dong_man_hinh_dang_cai_dat).
        self._man_hinh_dang_cai_dat = self._hien_man_hinh_dang_cai_dat()

        # Các việc chạy nền lúc khởi động: dò yt-dlp rồi tự cài plugin PO Token.
        # Đặt SAU _xay_dung_giao_dien() để khung Nhật ký đã tồn tại, ghi log được ngay.
        self._tu_dong_tim_ytdlp_khi_khoi_dong()

    def _hien_man_hinh_dang_cai_dat(self):
        """Hiện 1 cửa sổ nhỏ ĐÈ LÊN TRÊN và KHOÁ (modal, grab_set) toàn bộ cửa sổ
        chính, để người dùng KHÔNG bấm/gõ được gì (nhập URL, đổi thư mục, bấm Tải...)
        trong lúc chương trình đang tự dò/tải các công cụ cần thiết lúc mới mở (yt-dlp,
        ffmpeg, ffprobe, plugin PO Token, thư viện Thumbnails). Cũng chặn luôn nút X
        đóng cửa sổ NÀY (không phải cửa sổ chính) để tránh người dùng lỡ tưởng đây là
        hộp thoại thường rồi bấm tắt giữa chừng. Gọi _dong_man_hinh_dang_cai_dat() khi
        các bước chuẩn bị đã xong hết để mở khoá lại."""
        cua_so = tk.Toplevel(self.cua_so_goc)
        cua_so.title("Đang chuẩn bị...")
        cua_so.configure(bg=MAU_NEN)
        cua_so.resizable(False, False)
        cua_so.protocol("WM_DELETE_WINDOW", lambda: None)

        khung = tk.Frame(cua_so, bg=MAU_NEN, padx=36, pady=28)
        khung.pack()
        tk.Label(
            khung, text="Đang tự động kiểm tra/tải công cụ cần thiết...",
            bg=MAU_NEN, fg=MAU_CHU_CHINH, font=("Segoe UI", 11, "bold"),
        ).pack()
        tk.Label(
            khung,
            text="(yt-dlp, ffmpeg, ffprobe, plugin PO Token...)\n"
                 "Vui lòng chờ trong giây lát - xem chi tiết tiến độ ở khung Nhật ký.",
            bg=MAU_NEN, fg=MAU_CHU_PHU, font=FONT_THUONG, justify="center",
        ).pack(pady=(8, 0))

        try:
            self.cua_so_goc.update_idletasks()
            cua_so.update_idletasks()
            x = (self.cua_so_goc.winfo_x()
                 + (self.cua_so_goc.winfo_width() - cua_so.winfo_reqwidth()) // 2)
            y = (self.cua_so_goc.winfo_y()
                 + (self.cua_so_goc.winfo_height() - cua_so.winfo_reqheight()) // 2)
            cua_so.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except Exception:
            pass  # canh giữa chỉ để đẹp - lỗi thì thôi, không ảnh hưởng chức năng khoá

        cua_so.transient(self.cua_so_goc)
        cua_so.grab_set()  # KHOÁ - mọi thao tác chuột/bàn phím trên cửa sổ chính bị chặn
        return cua_so

    def _dong_man_hinh_dang_cai_dat(self):
        """Mở khoá lại cửa sổ chính sau khi các bước chuẩn bị lúc khởi động đã xong
        hết (dù thành công hay thất bại từng phần - xem chi tiết lỗi ở khung Nhật ký).
        An toàn khi gọi nhiều lần / gọi khi màn hình đã đóng."""
        cua_so = getattr(self, "_man_hinh_dang_cai_dat", None)
        if cua_so is not None:
            try:
                cua_so.grab_release()
                cua_so.destroy()
            except Exception:
                pass
            self._man_hinh_dang_cai_dat = None
        self._ghi_log("Đã chuẩn bị xong - có thể bắt đầu sử dụng chương trình.",
                      mau=MAU_THANH_CONG)

    def _ap_dung_style_ttk(self):
        """Tuỳ biến giao diện các widget kiểu ttk (Combobox, Scrollbar) cho khớp với
        bảng màu sáng - tối giản của toàn bộ chương trình, thay vì để mặc định xám
        cũ kiểu Windows 95 nhìn lệch tông với các nút bấm phẳng đã thiết kế riêng."""
        style = ttk.Style(self.cua_so_goc)
        try:
            style.theme_use("clam")  # theme 'clam' cho phép tuỳ biến màu sâu hơn theme mặc định
        except Exception:
            pass

        style.configure("TCombobox", fieldbackground=MAU_THE, background=MAU_THE,
                         foreground=MAU_CHU_CHINH, arrowcolor=MAU_CHU_CHINH,
                         bordercolor=MAU_VIEN, lightcolor=MAU_THE, darkcolor=MAU_THE,
                         padding=4)
        style.map("TCombobox",
                   fieldbackground=[("readonly", MAU_THE)],
                   selectbackground=[("readonly", MAU_THE)],
                   selectforeground=[("readonly", MAU_CHU_CHINH)])

        style.configure("Vertical.TScrollbar", background=MAU_VIEN, troughcolor=MAU_NEN,
                         bordercolor=MAU_NEN, arrowcolor=MAU_CHU_PHU, relief="flat")
        style.map("Vertical.TScrollbar", background=[("active", MAU_CHU_PHU)])

        # Tab (Notebook) - tab đang chọn có nền trắng + chữ đen ĐẬM (bold, không tô
        # màu) để nổi bật hẳn các tab chưa chọn (nền xám nhạt, chữ xám nhạt hơn).
        style.configure("TNotebook", background=MAU_NEN, borderwidth=0)
        style.configure("TNotebook.Tab", background=MAU_PHU_NHAT, foreground=MAU_CHU_PHU,
                         padding=(18, 10), font=FONT_NUT, borderwidth=0)
        style.map("TNotebook.Tab",
                   background=[("selected", MAU_THE)],
                   foreground=[("selected", MAU_NHAN)])

    def _dat_kich_thuoc_cua_so_theo_man_hinh(self):
        """Tự tính kích thước cửa sổ ban đầu dựa theo độ phân giải màn hình thật của máy,
        rồi canh giữa màn hình - để không bao giờ bị tràn ra ngoài / mất phần trên cùng
        như khi dùng kích thước cố định 680x760 trên màn hình nhỏ."""
        man_hinh_rong = self.cua_so_goc.winfo_screenwidth()
        man_hinh_cao = self.cua_so_goc.winfo_screenheight()

        rong = min(720, int(man_hinh_rong * 0.9))
        cao = min(760, int(man_hinh_cao * 0.85))
        # Chừa chỗ cho thanh tiêu đề/taskbar để cửa sổ không bị che mất phần trên
        cao = min(cao, man_hinh_cao - 80)

        x = max(0, (man_hinh_rong - rong) // 2)
        y = max(0, (man_hinh_cao - cao) // 2 - 20)

        self.cua_so_goc.geometry(f"{rong}x{cao}+{x}+{y}")
        self.cua_so_goc.minsize(520, 480)

    # ---------------- KHỐI GIAO DIỆN NHỎ TÁI SỬ DỤNG ----------------

    def _dat_icon_cua_so(self):
        """Đặt icon cho cửa sổ + thanh taskbar lúc đang chạy.
        Trên Windows dùng file .ico (được tkinter hỗ trợ SẴN, không cần Pillow).
        Trên macOS/Linux, .ico không dùng được cho iconbitmap - dùng iconphoto với
        file .png thay thế (cũng là định dạng tkinter đọc được sẵn từ Tk 8.6, không
        cần Pillow). Lưu ý: đây chỉ đổi icon LÚC CHẠY. Muốn đổi icon của chính FILE
        .exe khi nhìn trong File Explorer / trên màn hình Desktop thì phải đóng gói
        lại bằng lệnh pyinstaller có thêm cờ --icon=assets/icon.ico (xem hướng dẫn
        ở cuối file)."""
        try:
            if sys.platform == "win32":
                duong_dan_ico = duong_dan_tai_nguyen("icon.ico")
                if os.path.isfile(duong_dan_ico):
                    self.cua_so_goc.iconbitmap(duong_dan_ico)
            else:
                # iconphoto nhận NHIỀU ảnh cùng lúc, hệ điều hành tự chọn ảnh gần đúng
                # kích thước nhất cho từng chỗ hiển thị (taskbar nhỏ, alt-tab lớn hơn)
                # -> đưa cả icon.png (nhỏ, 1 lớp) LẪN banner.png (512x512, ảnh gốc nét
                # nhất hiện có trong assets/) để chỗ hiển thị lớn không bị vỡ nét/mờ.
                anh_cac_kich_thuoc = []
                for ten_file in ("icon.png", "banner.png"):
                    duong_dan = duong_dan_tai_nguyen(ten_file)
                    if os.path.isfile(duong_dan):
                        try:
                            anh_cac_kich_thuoc.append(tk.PhotoImage(file=duong_dan))
                        except Exception:
                            pass
                if anh_cac_kich_thuoc:
                    # Giữ tham chiếu (self._anh_icon_cua_so) để ảnh không bị dọn rác
                    # giữa chừng - tkinter không tự giữ tham chiếu ảnh PhotoImage.
                    self._anh_icon_cua_so = anh_cac_kich_thuoc
                    self.cua_so_goc.iconphoto(True, *anh_cac_kich_thuoc)
        except Exception:
            pass

    def _the(self, cha, **kwargs):
        """1 khối 'card' nền trắng, viền mỏng, bo góc nhẹ (mô phỏng bằng border thường)."""
        khung = tk.Frame(cha, bg=MAU_THE, highlightbackground=MAU_VIEN,
                          highlightthickness=1, bd=0)
        return khung

    def _o_nhap(self, cha, **kwargs):
        """Ô nhập liệu viền mỏng, TỰ ĐỔI màu viền sang đỏ điểm nhấn khi người dùng
        bấm vào (focus) để rõ ràng đây là ô đang gõ, rồi trả lại màu viền xám nhạt
        bình thường khi rời khỏi ô - giúp giao diện có phản hồi thị giác sống động
        hơn thay vì viền tĩnh một màu suốt."""
        o = tk.Entry(cha, font=FONT_THUONG, bg=MAU_THE, fg=MAU_CHU_CHINH,
                     relief="solid", bd=1, highlightbackground=MAU_VIEN,
                     highlightcolor=MAU_NHAN, highlightthickness=1,
                     insertbackground=MAU_CHU_CHINH, **kwargs)
        return o

    def _nhan_muc(self, cha, chu):
        return tk.Label(cha, text=chu, font=FONT_TIEU_DE_MUC, bg=MAU_NEN, fg=MAU_CHU_CHINH,
                         anchor="w")

    def _nhan_phu(self, cha, chu):
        return tk.Label(cha, text=chu, font=FONT_NHAN, bg=MAU_NEN, fg=MAU_CHU_PHU, anchor="w",
                         justify="left", wraplength=560)

    # ---------------- XÂY DỰNG GIAO DIỆN ----------------

    def _tao_logo(self, cha):
        """Trả về 1 khung chứa logo chương trình: ưu tiên dùng ảnh thật
        (assets/icon_banner.png), TỰ ĐỘNG rơi về hình vẽ mũi tên tải xuống bằng
        tkinter thuần nếu vì lý do gì đó không đọc được file ảnh (VD file bị thiếu
        khi copy chương trình sang máy khác) - đảm bảo banner luôn hiển thị được
        gì đó thay vì báo lỗi/để trống."""
        KICH_THUOC_LOGO = 40
        khung_logo = tk.Frame(cha, width=KICH_THUOC_LOGO, height=KICH_THUOC_LOGO,
                               bg=MAU_NEN)
        khung_logo.pack_propagate(False)

        duong_dan_anh = duong_dan_tai_nguyen("icon_banner.png")
        anh_logo = None
        try:
            if os.path.isfile(duong_dan_anh):
                anh_goc = tk.PhotoImage(file=duong_dan_anh)
                # Ảnh nguồn 80x80 -> co còn đúng 40x40 (chia nguyên 2 lần) để nét,
                # không dùng phép nội suy tuỳ ý (tk.PhotoImage không hỗ trợ).
                anh_logo = anh_goc.subsample(2, 2)
        except Exception:
            anh_logo = None

        if anh_logo is not None:
            # QUAN TRỌNG: giữ tham chiếu ảnh trên chính đối tượng self (không phải
            # biến cục bộ) - nếu không, Python sẽ dọn rác PhotoImage ngay khi hàm
            # này kết thúc, khiến logo hiển thị trống trơn dù code không hề báo lỗi.
            self._anh_logo_banner = anh_logo
            tk.Label(khung_logo, image=anh_logo, bg=MAU_NEN, bd=0,
                     highlightthickness=0).pack(expand=True)
        else:
            # Phương án dự phòng: khối vuông viền đậm + ký hiệu tải xuống, vẽ hoàn
            # toàn bằng tkinter thuần (giữ đúng phong cách logo trước đây).
            khung_du_phong = tk.Frame(khung_logo, bg=MAU_LOGO_NEN,
                                       highlightbackground=MAU_LOGO_VIEN,
                                       highlightthickness=2)
            khung_du_phong.pack(fill="both", expand=True)
            tk.Label(khung_du_phong, text="⬇", font=("Segoe UI", 14, "bold"),
                     bg=MAU_LOGO_NEN, fg=MAU_LOGO_VIEN).pack(expand=True)

        return khung_logo

    def _ve_banner(self, cha):
        """Vẽ phần tiêu đề đầu cửa sổ: logo + tên chương trình + mô tả ngắn, cùng
        1 nút nhỏ bên phải để đổi qua lại giữa giao diện Sáng/Tối."""
        khung = tk.Frame(cha, bg=MAU_NEN)
        khung.grid(row=0, column=0, sticky="ew", pady=(0, 16))

        khung_dong_1 = tk.Frame(khung, bg=MAU_NEN)
        khung_dong_1.pack(fill="x")

        self._tao_logo(khung_dong_1).pack(side="left", padx=(0, 10))

        khung_chu = tk.Frame(khung_dong_1, bg=MAU_NEN)
        khung_chu.pack(side="left", fill="both", expand=True)
        tk.Label(khung_chu, text=TEN_CHUONG_TRINH, font=FONT_TIEU_DE,
                 bg=MAU_NEN, fg=MAU_CHU_CHINH, anchor="w").pack(fill="x")
        tk.Label(khung_chu, text="Dùng yt-dlp làm trung gian tải video",
                 font=FONT_PHU_DE, bg=MAU_NEN, fg=MAU_CHU_PHU, anchor="w").pack(fill="x")

        # Nút nhỏ đổi giao diện Sáng/Tối, đặt góc phải banner - luôn hiện chữ của
        # giao diện SẼ chuyển TỚI (đang ở Sáng -> hiện "Tối", đang ở Tối -> hiện "Sáng").
        dang_toi = _giao_dien_hien_tai == "toi"
        chu_nut = "☀ Sáng" if dang_toi else "🌙 Tối"
        self.nut_doi_giao_dien = NutTrangTron(
            khung_dong_1, text=chu_nut, command=self._doi_giao_dien)
        self.nut_doi_giao_dien.configure(padx=10, pady=6, font=FONT_NHAN)
        self.nut_doi_giao_dien.pack(side="right", anchor="n", padx=(10, 0))

        # 1 đường kẻ mỏng ngăn cách tiêu đề với phần nội dung phía dưới
        tk.Frame(khung, bg=MAU_VIEN, height=1).pack(fill="x", pady=(14, 0))

    def _tao_khung_tren_cuon(self, cha):
        """Tạo khung phần trên (cấu hình + nút bấm) có thể CUỘN được bằng Canvas + Scrollbar.
        Nhờ vậy khi nội dung 1 tab dài hơn khung cho phép (VD tab Thumbnails có nhiều
        trường hơn tab Video), các trường nhập liệu KHÔNG bao giờ bị che/mất - người
        dùng chỉ cần cuộn lên xuống để thấy đầy đủ, thay vì bị cắt mất."""
        vo_ngoai = tk.Frame(cha, bg=MAU_NEN)
        vo_ngoai.grid(row=0, column=0, sticky="nsew")
        vo_ngoai.rowconfigure(0, weight=1)
        vo_ngoai.columnconfigure(0, weight=1)

        canvas = tk.Canvas(vo_ngoai, bg=MAU_NEN, highlightthickness=0, bd=0)
        thanh_cuon = ttk.Scrollbar(vo_ngoai, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=thanh_cuon.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        thanh_cuon.grid(row=0, column=1, sticky="ns")

        khung_noi_dung = tk.Frame(canvas, bg=MAU_NEN)
        id_cua_so = canvas.create_window((0, 0), window=khung_noi_dung, anchor="nw")

        def _cap_nhat_vung_cuon(_event=None):
            # Bọc try/except: khi cửa sổ bị đóng trong lúc còn tiến trình nền đang
            # chạy, canvas này có thể đã bị huỷ nhưng sự kiện <Configure> vẫn kịp bắn
            # ra 1 lần cuối - bỏ qua an toàn thay vì in traceback lúc thoát chương trình.
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
                hop = canvas.bbox("all")
            except tk.TclError:
                return
            if not hop:
                return
            chieu_cao_noi_dung = hop[3] - hop[1]
            # QUAN TRỌNG: chiều cao vùng cuộn được giới hạn ở 1 mức CỐ ĐỊNH
            # (GIOI_HAN_CHIEU_CAO_VUNG_CUON), KHÔNG tính theo chiều cao cửa sổ như
            # bản trước. Bản trước lấy chiều cao cửa sổ trừ đi vài số cố định, nhưng
            # KHÔNG trừ đúng hết các phần chiếm chỗ khác (banner, thanh tab, hàng nút
            # bấm cố định của từng tab) - khiến tổng chiều cao thật sự cần lớn hơn
            # cửa sổ mặc định, đẩy khung "Thông tin" lọt ra ngoài vùng nhìn thấy và
            # CHỈ HIỆN RA khi phóng to cửa sổ đủ lớn. Dùng 1 mức cố định ở đây, kết
            # hợp với việc đặt sẵn chiều cao cố định cho cả khối Notebook (xem
            # _xay_dung_giao_dien), giúp tổng chiều cao mọi thành phần luôn CỐ ĐỊNH
            # và nhỏ hơn chắc chắn kích thước cửa sổ mặc định - khung "Thông tin" vì
            # vậy luôn có chỗ hiển thị ngay từ đầu, không cần phóng to cửa sổ.
            try:
                canvas.configure(height=min(chieu_cao_noi_dung, GIOI_HAN_CHIEU_CAO_VUNG_CUON))
            except tk.TclError:
                return

        def _cap_nhat_be_rong(event):
            # Cho nội dung bên trong giãn theo đúng bề rộng canvas khi cửa sổ đổi kích thước
            canvas.itemconfig(id_cua_so, width=event.width)

        khung_noi_dung.bind("<Configure>", _cap_nhat_vung_cuon)
        canvas.bind("<Configure>", _cap_nhat_be_rong)

        def _cuon_chuot(event):
            if sys.platform == "darwin":
                canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _cuon_chuot_linux(event):
            canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

        # Chỉ lăn chuột được khi con trỏ đang ở trong khu vực phần trên (tránh xung đột
        # với việc cuộn khung Thông tin bên dưới)
        def _gan_cuon(_e=None):
            canvas.bind_all("<MouseWheel>", _cuon_chuot)
            canvas.bind_all("<Button-4>", _cuon_chuot_linux)
            canvas.bind_all("<Button-5>", _cuon_chuot_linux)

        def _thao_cuon(_e=None):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _gan_cuon)
        canvas.bind("<Leave>", _thao_cuon)

        return khung_noi_dung

    def _xay_dung_giao_dien(self):
        khung_ngoai = tk.Frame(self.cua_so_goc, bg=MAU_NEN, padx=20, pady=18)
        khung_ngoai.pack(fill="both", expand=True)
        self.khung_ngoai = khung_ngoai

        # row 0: banner (cố định) | row 1: notebook 2 tab (cố định) | row 2: khung
        # "Thông tin" dùng chung cho cả 2 tab, nhận hết khoảng trống dư ra khi phóng
        # to cửa sổ.
        khung_ngoai.grid_rowconfigure(0, weight=0)
        khung_ngoai.grid_rowconfigure(1, weight=0)
        khung_ngoai.grid_rowconfigure(2, weight=1, minsize=140)
        khung_ngoai.grid_columnconfigure(0, weight=1)

        self._ve_banner(khung_ngoai)

        so_tay = ttk.Notebook(khung_ngoai, height=CHIEU_CAO_NOTEBOOK)
        so_tay.grid(row=1, column=0, sticky="ew")
        self.so_tay = so_tay

        tab_video = tk.Frame(so_tay, bg=MAU_NEN)
        tab_thumbnail = tk.Frame(so_tay, bg=MAU_NEN)
        so_tay.add(tab_video, text="Tải video")
        so_tay.add(tab_thumbnail, text="Tải Thumbnails")

        self._xay_dung_tab_video(tab_video)
        self._xay_dung_tab_thumbnail(tab_thumbnail)

        # --- Card thông tin (dùng chung cho cả 2 tab, co dãn theo phần trống còn lại
        # của cửa sổ - xem grid_rowconfigure ở trên) ---
        khung_duoi = tk.Frame(khung_ngoai, bg=MAU_NEN)
        khung_duoi.grid(row=2, column=0, sticky="nsew", pady=(12, 0))

        self._nhan_muc(khung_duoi, "Thông tin").pack(fill="x")
        the_log = self._the(khung_duoi)
        the_log.pack(fill="both", expand=True, pady=(4, 0))
        self.khung_log = scrolledtext.ScrolledText(
            the_log, font=FONT_MONO, bg=MAU_THE, fg=MAU_CHU_CHINH,
            relief="flat", bd=0, padx=10, pady=8, state="disabled", wrap="word",
        )
        self.khung_log.pack(fill="both", expand=True)

    # ---------------- ĐỔI GIAO DIỆN SÁNG / TỐI ----------------

    # Danh sách các Ô NHẬP (Entry/Spinbox) cần giữ nguyên nội dung khi đổi giao
    # diện - liệt kê tên thuộc tính (attribute) đúng như trong _xay_dung_tab_video /
    # _xay_dung_tab_thumbnail. Nếu sau này thêm ô nhập mới, chỉ cần thêm tên vào đây.
    _CAC_O_NHAP_CAN_GIU = [
        "o_ytdlp", "o_url", "o_tu_video", "o_den_video", "o_thu_muc",
        "o_url_thumb", "o_thu_muc_thumb", "o_api_key", "o_tu_video_thumb",
        "o_den_video_thumb", "o_hue", "o_saturation",
        "o_value",
    ]
    # Các biến BooleanVar (checkbox) cần giữ nguyên trạng thái bật/tắt.
    _CAC_BIEN_BOOL_CAN_GIU = [
        "bien_shorts", "bien_bo_qua_shorts_thumb",
        "bien_chi_am_thanh", "bien_nhung_phu_de", "bien_nhung_metadata",
        "bien_dung_cookie",
    ]

    def _doc_log_kem_tag(self):
        """Đọc toàn bộ nội dung khung log kèm TÊN tag màu (nếu có) của từng đoạn chữ,
        để _khoi_phuc_trang_thai_giao_dien có thể tô lại đúng Ý NGHĨA màu (thành
        công/lỗi/phụ) theo bảng màu MỚI - thay vì mất màu hoặc lỡ giữ nguyên màu cũ
        không hợp với giao diện mới sau khi đổi Sáng/Tối."""
        doan = []
        tag_dang_mo = []
        for khoa, gia_tri, _chi_so in self.khung_log.dump("1.0", "end-1c", tag=True, text=True):
            if khoa == "tagon":
                tag_dang_mo.append(gia_tri)
            elif khoa == "tagoff" and gia_tri in tag_dang_mo:
                tag_dang_mo.remove(gia_tri)
            elif khoa == "text":
                doan.append((gia_tri, tag_dang_mo[-1] if tag_dang_mo else None))
        return doan

    def _chup_trang_thai_giao_dien(self):
        """Ghi lại toàn bộ nội dung người dùng đã nhập/chọn TRƯỚC khi dựng lại giao
        diện theo bảng màu mới, để khôi phục lại y hệt SAU khi dựng xong - tránh
        việc đổi giao diện làm mất trắng URL/thư mục/API key đang gõ dở."""
        trang_thai = {"o_nhap": {}, "bool": {}}
        for ten in self._CAC_O_NHAP_CAN_GIU:
            o = getattr(self, ten, None)
            if o is not None:
                try:
                    trang_thai["o_nhap"][ten] = o.get()
                except Exception:
                    pass
        for ten in self._CAC_BIEN_BOOL_CAN_GIU:
            bien = getattr(self, ten, None)
            if bien is not None:
                try:
                    trang_thai["bool"][ten] = bien.get()
                except Exception:
                    pass
        try:
            trang_thai["chat_luong"] = self.o_chat_luong.current()
        except Exception:
            trang_thai["chat_luong"] = -1
        try:
            trang_thai["kieu_ten_file"] = self.o_kieu_ten_file.current()
        except Exception:
            trang_thai["kieu_ten_file"] = -1
        try:
            trang_thai["log_doan"] = self._doc_log_kem_tag()
        except Exception:
            trang_thai["log_doan"] = []
        try:
            trang_thai["tab"] = self.so_tay.index(self.so_tay.select())
        except Exception:
            trang_thai["tab"] = 0
        return trang_thai

    def _khoi_phuc_trang_thai_giao_dien(self, trang_thai):
        """Điền lại đúng những gì đã ghi ở _chup_trang_thai_giao_dien vào bộ widget
        VỪA được dựng lại (widget mới hoàn toàn nên luôn rỗng/mặc định lúc này)."""
        for ten, gia_tri in trang_thai.get("o_nhap", {}).items():
            o = getattr(self, ten, None)
            if o is None or not gia_tri:
                continue
            try:
                o.delete(0, "end")
                o.insert(0, gia_tri)
            except Exception:
                pass
        for ten, gia_tri in trang_thai.get("bool", {}).items():
            bien = getattr(self, ten, None)
            if bien is not None:
                try:
                    bien.set(gia_tri)
                except Exception:
                    pass
        chi_so_chat_luong = trang_thai.get("chat_luong", -1)
        if chi_so_chat_luong is not None and chi_so_chat_luong >= 0:
            try:
                self.o_chat_luong.current(chi_so_chat_luong)
            except Exception:
                pass
        chi_so_kieu_ten = trang_thai.get("kieu_ten_file", -1)
        if chi_so_kieu_ten is not None and chi_so_kieu_ten >= 0:
            try:
                self.o_kieu_ten_file.current(chi_so_kieu_ten)
            except Exception:
                pass
        log_doan = trang_thai.get("log_doan")
        if log_doan:
            try:
                self.khung_log.configure(state="normal")
                for doan_chu, ten_tag in log_doan:
                    if ten_tag:
                        ten_bien = ten_tag[len("tag_"):] if ten_tag.startswith("tag_") else ten_tag
                        mau_moi = globals().get(ten_bien)
                        if mau_moi:
                            self.khung_log.tag_config(ten_tag, foreground=mau_moi)
                        self.khung_log.insert("end", doan_chu, ten_tag)
                    else:
                        self.khung_log.insert("end", doan_chu)
                self.khung_log.see("end")
                self.khung_log.configure(state="disabled")
            except Exception:
                pass
        try:
            self.so_tay.select(trang_thai.get("tab", 0))
        except Exception:
            pass
        # Khôi phục đúng trạng thái nút "2) Bắt đầu tải" theo danh sách video còn
        # thiếu đã đếm được từ trước (nếu có) - widget mới mặc định luôn khoá lại.
        try:
            if self.danh_sach_thieu:
                self.nut_tai.configure(state="normal")
        except Exception:
            pass

    def _doi_giao_dien(self):
        """Đổi qua lại giữa giao diện Sáng <-> Tối: chụp lại trạng thái các ô nhập,
        dựng lại TOÀN BỘ khung nội dung theo bảng màu mới, rồi điền lại trạng thái
        cũ vào khung mới. CHẶN việc đổi khi đang có tác vụ chạy ngầm (tải video/
        thumbnail) để tránh các luồng nền gọi vào widget cũ đã bị huỷ."""
        dang_ban = (getattr(self, "_so_tien_trinh_dang_chay", 0) or 0) > 0 \
            or getattr(self, "_dang_tai_thumbnail", False)
        if dang_ban:
            messagebox.showinfo(
                "Không thể đổi giao diện lúc này",
                "Vui lòng đợi tác vụ tải hiện tại hoàn tất (hoặc bấm Tạm dừng/Huỷ) "
                "rồi hãy đổi giao diện."
            )
            return

        giao_dien_moi = "sang" if _giao_dien_hien_tai == "toi" else "toi"
        trang_thai = self._chup_trang_thai_giao_dien()

        ap_dung_bang_mau(giao_dien_moi)
        luu_giao_dien(giao_dien_moi)

        self.khung_ngoai.destroy()
        self.cua_so_goc.configure(bg=MAU_NEN)
        self._ap_dung_style_ttk()
        self._xay_dung_giao_dien()
        self._khoi_phuc_trang_thai_giao_dien(trang_thai)

    def _xay_dung_tab_video(self, tab_cha):
        """Xây nội dung tab 'Tải video' - y hệt phần cấu hình + nút bấm trước đây,
        nay đặt bên trong 1 tab của Notebook thay vì chiếm toàn bộ cửa sổ."""
        tab_cha.grid_rowconfigure(0, weight=0)
        tab_cha.grid_rowconfigure(1, weight=0)
        tab_cha.grid_columnconfigure(0, weight=1)

        khung_tren = self._tao_khung_tren_cuon(tab_cha)

        # --- Card cấu hình ---
        the_cau_hinh = self._the(khung_tren)
        the_cau_hinh.pack(fill="x", pady=(12, 12))
        noi_dung = tk.Frame(the_cau_hinh, bg=MAU_THE, padx=16, pady=14)
        noi_dung.pack(fill="x")

        self._nhan_muc(noi_dung, "Đường dẫn yt-dlp").grid(row=0, column=0, sticky="w", columnspan=2)
        hang_ytdlp = tk.Frame(noi_dung, bg=MAU_THE)
        hang_ytdlp.grid(row=1, column=0, columnspan=2, sticky="we", pady=(4, 10))
        hang_ytdlp.columnconfigure(0, weight=1)
        self.o_ytdlp = self._o_nhap(hang_ytdlp)
        self.o_ytdlp.grid(row=0, column=0, sticky="we", padx=(0, 8))
        NutTrangTron(hang_ytdlp, text="Chọn file...", command=self._chon_file_ytdlp).grid(row=0, column=1, padx=(0, 8))
        self.nut_cap_nhat_ytdlp = NutTrangTron(hang_ytdlp, text="🔄 Cập nhật yt-dlp",
                                                command=self._kiem_tra_cap_nhat_ytdlp)
        self.nut_cap_nhat_ytdlp.grid(row=0, column=2)

        self._nhan_muc(noi_dung, "URL kênh YouTube").grid(row=2, column=0, sticky="w", columnspan=2)
        self.o_url = self._o_nhap(noi_dung)
        self.o_url.grid(row=3, column=0, columnspan=2, sticky="we", pady=(4, 10))

        self.bien_shorts = tk.BooleanVar(value=False)
        tk.Checkbutton(noi_dung, text="Tải cả video Shorts", variable=self.bien_shorts,
                        bg=MAU_THE, fg=MAU_CHU_CHINH, font=FONT_THUONG,
                        activebackground=MAU_THE, selectcolor=MAU_THE,
                        anchor="w").grid(row=4, column=0, sticky="w", pady=(0, 10))

        # --- Khoảng video cần tải (STT tính theo kênh, 1 = video MỚI NHẤT) ---
        # Để trống CẢ HAI ô -> mặc định tải TẤT CẢ (giữ nguyên hành vi cũ).
        self._nhan_muc(noi_dung, "Khoảng video cần tải (để trống = tải tất cả)").grid(
            row=5, column=0, columnspan=2, sticky="w")
        khung_khoang = tk.Frame(noi_dung, bg=MAU_THE)
        khung_khoang.grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 2))
        tk.Label(khung_khoang, text="Từ video số", font=FONT_NHAN, bg=MAU_THE,
                 fg=MAU_CHU_PHU).pack(side="left")
        self.o_tu_video = tk.Entry(khung_khoang, font=FONT_THUONG, width=6, bg=MAU_THE,
                                    fg=MAU_CHU_CHINH, relief="solid", bd=1,
                                    highlightbackground=MAU_VIEN, highlightthickness=1,
                                    justify="center")
        self.o_tu_video.pack(side="left", padx=(6, 14))
        tk.Label(khung_khoang, text="đến video số", font=FONT_NHAN, bg=MAU_THE,
                 fg=MAU_CHU_PHU).pack(side="left")
        self.o_den_video = tk.Entry(khung_khoang, font=FONT_THUONG, width=6, bg=MAU_THE,
                                     fg=MAU_CHU_CHINH, relief="solid", bd=1,
                                     highlightbackground=MAU_VIEN, highlightthickness=1,
                                     justify="center")
        self.o_den_video.pack(side="left", padx=(6, 0))
        self._nhan_phu(
            noi_dung,
            "STT tính theo thứ tự trên kênh, 1 = video MỚI NHẤT (VD: Từ 1 đến 50 = 50 video "
            "mới nhất). Video đã tải rồi trong thư mục vẫn được tự động bỏ qua như trước."
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self._nhan_muc(noi_dung, "Thư mục lưu video").grid(row=8, column=0, sticky="w", columnspan=2)
        hang_thu_muc = tk.Frame(noi_dung, bg=MAU_THE)
        hang_thu_muc.grid(row=9, column=0, columnspan=2, sticky="we", pady=(4, 2))
        hang_thu_muc.columnconfigure(0, weight=1)
        self.o_thu_muc = self._o_nhap(hang_thu_muc)
        self.o_thu_muc.grid(row=0, column=0, sticky="we", padx=(0, 8))
        NutTrangTron(hang_thu_muc, text="Chọn thư mục...", command=self._chon_thu_muc).grid(row=0, column=1)
        self._nhan_phu(
            noi_dung,
            f"Chỉ gõ tên -> tự tạo trong {core.O_DIA_MAC_DINH} · gõ đường dẫn đầy đủ -> lưu đúng chỗ đó"
        ).grid(row=10, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self._nhan_muc(noi_dung, "Chất lượng video *").grid(row=11, column=0, sticky="w")
        self._nhan_hien_thi_chat_luong = [nhan for _gt, nhan in core.DANH_SACH_CHAT_LUONG]
        self.o_chat_luong = ttk.Combobox(noi_dung, values=self._nhan_hien_thi_chat_luong,
                                          state="readonly", width=26, font=FONT_THUONG)
        # CỐ Ý KHÔNG đặt sẵn giá trị mặc định (không gọi .current(...)) - để ô này
        # hiển thị TRỐNG, bắt người dùng phải tự bấm chọn 1 mức chất lượng trước khi
        # tải được (xem kiểm tra bắt buộc trong _bat_dau_tai). Trước đây có đặt sẵn
        # "720p" làm mặc định, nhưng gây hiểu lầm mức đang chọn thực sự là gì mỗi khi
        # tải nhiều đợt khác chất lượng nhau - bắt chọn tay mỗi lần sẽ rõ ràng hơn.
        self.o_chat_luong.grid(row=12, column=0, sticky="w", pady=(4, 0))

        self._nhan_muc(noi_dung, "Kiểu đặt tên file").grid(row=11, column=1, sticky="w", padx=(16, 0))
        self._ma_kieu_ten_file = [ma for ma, _nhan, _mau in core.DANH_SACH_KIEU_TEN_FILE]
        self.o_kieu_ten_file = ttk.Combobox(
            noi_dung,
            values=[nhan for _ma, nhan, _mau in core.DANH_SACH_KIEU_TEN_FILE],
            state="readonly", width=26, font=FONT_THUONG)
        self.o_kieu_ten_file.current(0)
        self.o_kieu_ten_file.grid(row=12, column=1, sticky="w", padx=(16, 0), pady=(4, 0))

        # --- Tuỳ chọn nâng cao (lấy cảm hứng từ các tính năng của YoutubeDownloader) ---
        self._nhan_muc(noi_dung, "Tuỳ chọn nâng cao").grid(
            row=13, column=0, columnspan=2, sticky="w", pady=(14, 0))

        khung_tuy_chon = tk.Frame(noi_dung, bg=MAU_THE)
        khung_tuy_chon.grid(row=14, column=0, columnspan=2, sticky="w", pady=(4, 4))

        self.bien_chi_am_thanh = tk.BooleanVar(value=False)
        tk.Checkbutton(khung_tuy_chon, text="Chỉ tải âm thanh (MP3)", variable=self.bien_chi_am_thanh,
                        bg=MAU_THE, fg=MAU_CHU_CHINH, font=FONT_THUONG,
                        activebackground=MAU_THE, selectcolor=MAU_THE,
                        anchor="w").pack(side="left", padx=(0, 16))

        self.bien_nhung_phu_de = tk.BooleanVar(value=False)
        tk.Checkbutton(khung_tuy_chon, text="Nhúng phụ đề (nếu có)", variable=self.bien_nhung_phu_de,
                        bg=MAU_THE, fg=MAU_CHU_CHINH, font=FONT_THUONG,
                        activebackground=MAU_THE, selectcolor=MAU_THE,
                        anchor="w").pack(side="left", padx=(0, 16))

        self.bien_nhung_metadata = tk.BooleanVar(value=False)
        tk.Checkbutton(khung_tuy_chon, text="Nhúng thông tin & ảnh bìa", variable=self.bien_nhung_metadata,
                        bg=MAU_THE, fg=MAU_CHU_CHINH, font=FONT_THUONG,
                        activebackground=MAU_THE, selectcolor=MAU_THE,
                        anchor="w").pack(side="left")

        # --- Cookie: CÔNG TẮC DUY NHẤT - dùng hoặc không dùng, không còn liên quan gì
        # tới việc chất lượng có bị hạ hay không. BẬT thì MỌI video trong đợt tải đều
        # tải kèm cookie NGAY TỪ LƯỢT ĐẦU TIÊN; TẮT thì KHÔNG video nào dùng cookie cả.
        self.bien_dung_cookie = tk.BooleanVar(value=False)
        self.bien_dung_cookie.trace_add("write", lambda *_args: self._khi_bat_tat_cookie())
        tk.Checkbutton(
            noi_dung, text="Dùng cookie đăng nhập YouTube",
            variable=self.bien_dung_cookie,
            bg=MAU_THE, fg=MAU_CHU_CHINH, font=FONT_THUONG,
            activebackground=MAU_THE, selectcolor=MAU_THE,
            anchor="w").grid(row=15, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self._nhan_phu(
            noi_dung,
            "BẬT: mọi video trong đợt tải đều tải kèm cookie ngay từ đầu. TẮT: không video "
            "nào dùng cookie. Cần thiết lập Extension và bấm gửi cookie trong popup của nó "
            "TRƯỚC khi tích ô này (nút \"🧩 Thiết lập Extension đọc cookie\" bên dưới - chỉ "
            "cần thiết lập 1 lần). Sẽ báo rõ trong khung Thông tin có đọc được cookie hay không."
        ).grid(row=16, column=0, columnspan=2, sticky="w", pady=(0, 4))

        tk.Button(
            noi_dung, text="🧩 Thiết lập Extension đọc cookie (khuyên dùng)",
            command=self._thiet_lap_extension_cookie,
            bg=MAU_THE, fg=MAU_CHU_CHINH, font=FONT_THUONG,
            relief="groove", cursor="hand2",
        ).grid(row=17, column=0, columnspan=2, sticky="w", pady=(0, 4))

        noi_dung.columnconfigure(0, weight=1)

        # --- Nút hành động (KHÔNG nằm trong vùng cuộn - luôn hiển thị đầy đủ, cố định) ---
        khung_co_dinh = tk.Frame(tab_cha, bg=MAU_NEN)
        khung_co_dinh.grid(row=1, column=0, sticky="ew", pady=(10, 12))

        khung_nut = tk.Frame(khung_co_dinh, bg=MAU_NEN)
        khung_nut.pack(fill="x", pady=(0, 8))
        self.nut_dem = NutTrangTron(khung_nut, text="1) Đếm video & quét file đã tải",
                                     command=self._bat_dau_dem_va_quet)
        self.nut_dem.pack(side="left")
        self.nut_tai = NutDen(khung_nut, text="2) Bắt đầu tải", command=self._bat_dau_tai,
                              state="disabled")
        self.nut_tai.pack(side="left", padx=(10, 0))
        self.nut_tam_dung = NutCanhBao(khung_nut, text="⏸ Tạm dừng",
                                        command=self._tam_dung_tiep_tuc, state="disabled")
        self.nut_tam_dung.pack(side="left", padx=(10, 0))

        # --- Trạng thái ngắn gọn (kèm 1 chấm tròn màu đổi theo tình trạng hiện tại) ---
        khung_trang_thai = tk.Frame(khung_co_dinh, bg=MAU_NEN)
        khung_trang_thai.pack(fill="x", pady=(0, 0))
        self.diem_trang_thai = tk.Label(khung_trang_thai, text="●", font=("Segoe UI", 9),
                                         bg=MAU_NEN, fg=MAU_DIEM_TRANG_THAI_SAN_SANG)
        self.diem_trang_thai.pack(side="left")
        self.nhan_trang_thai = tk.Label(khung_trang_thai, text="Sẵn sàng.", font=FONT_NHAN,
                                         bg=MAU_NEN, fg=MAU_CHU_PHU, anchor="w")
        self.nhan_trang_thai.pack(side="left", padx=(4, 0))

    def _xay_dung_tab_thumbnail(self, tab_cha):
        """Xây nội dung tab 'Tải Thumbnails': URL kênh, thư mục lưu, API key,
        số lượng ảnh, tuỳ chọn chỉnh màu, số luồng song song, nút Đếm + Tải + Huỷ."""
        tab_cha.grid_rowconfigure(0, weight=0)
        tab_cha.grid_rowconfigure(1, weight=0)
        tab_cha.grid_columnconfigure(0, weight=1)

        khung_tren = self._tao_khung_tren_cuon(tab_cha)

        the_cau_hinh = self._the(khung_tren)
        the_cau_hinh.pack(fill="x", pady=(12, 12))
        noi_dung = tk.Frame(the_cau_hinh, bg=MAU_THE, padx=16, pady=14)
        noi_dung.pack(fill="x")

        hang = 0
        self._nhan_muc(noi_dung, "Link kênh YouTube (lấy thumbnail)").grid(
            row=hang, column=0, sticky="w", columnspan=2); hang += 1
        self.o_url_thumb = self._o_nhap(noi_dung)
        self.o_url_thumb.grid(row=hang, column=0, columnspan=2, sticky="we", pady=(4, 10)); hang += 1

        self._nhan_muc(noi_dung, "Thư mục lưu thumbnails").grid(
            row=hang, column=0, sticky="w", columnspan=2); hang += 1
        hang_thu_muc = tk.Frame(noi_dung, bg=MAU_THE)
        hang_thu_muc.grid(row=hang, column=0, columnspan=2, sticky="we", pady=(4, 2)); hang += 1
        hang_thu_muc.columnconfigure(0, weight=1)
        self.o_thu_muc_thumb = self._o_nhap(hang_thu_muc)
        self.o_thu_muc_thumb.grid(row=0, column=0, sticky="we", padx=(0, 8))
        NutTrangTron(hang_thu_muc, text="Chọn thư mục...",
                     command=self._chon_thu_muc_thumb).grid(row=0, column=1)
        self._nhan_phu(
            noi_dung,
            f"Chỉ gõ tên -> tự tạo trong {core.O_DIA_MAC_DINH} · gõ đường dẫn đầy đủ -> lưu đúng chỗ đó"
        ).grid(row=hang, column=0, columnspan=2, sticky="w", pady=(0, 10)); hang += 1

        self._nhan_muc(noi_dung, "YouTube Data API key").grid(
            row=hang, column=0, sticky="w", columnspan=2); hang += 1
        hang_api = tk.Frame(noi_dung, bg=MAU_THE)
        hang_api.grid(row=hang, column=0, columnspan=2, sticky="we", pady=(4, 2)); hang += 1
        hang_api.columnconfigure(0, weight=1)
        self.o_api_key = self._o_nhap(hang_api, show="•")
        self.o_api_key.grid(row=0, column=0, sticky="we", padx=(0, 8))
        api_key_da_luu = thumb_core.doc_api_key()
        if api_key_da_luu:
            self.o_api_key.insert(0, api_key_da_luu)
        NutTrangTron(hang_api, text="Lưu key", command=self._luu_api_key).grid(row=0, column=1)
        self.nut_tu_dong_lay_key = NutTrangTron(hang_api, text="🪄 Tự động lấy",
                                                  command=self._tu_dong_lay_api_key)
        self.nut_tu_dong_lay_key.grid(row=0, column=2, padx=(8, 0))
        self._nhan_phu(
            noi_dung,
            "Lấy miễn phí tại Google Cloud Console (bật 'YouTube Data API v3'), hoặc bấm "
            "'🪄 Tự động lấy' để chương trình tự làm giúp phần lớn các bước (vẫn cần bạn "
            "đăng nhập Google 1 lần qua trình duyệt - yêu cầu bảo mật của Google, không thể "
            "bỏ qua). Key được lưu vào file cạnh chương trình, không gửi đi đâu khác."
        ).grid(row=hang, column=0, columnspan=2, sticky="w", pady=(0, 10)); hang += 1

        hang_tuy_chon_1 = hang
        hang += 2  # khối này chiếm 2 hàng lưới (nhãn + ô nhập), phải tăng đúng 2 để
                   # tránh hàng tiếp theo (checkbox Shorts) đè lên ô nhập bên dưới

        # --- Khoảng video cần tải thumbnail (1 = video MỚI NHẤT, giống hệt cách đánh
        # số bên tab "Tải video" để 2 tab dùng chung 1 cách hiểu). Để trống cả 2 ô ->
        # mặc định tải TẤT CẢ.
        self._nhan_muc(noi_dung, "Khoảng video cần tải (để trống = tất cả)").grid(
            row=hang_tuy_chon_1, column=0, sticky="w")
        khung_khoang_thumb = tk.Frame(noi_dung, bg=MAU_THE)
        khung_khoang_thumb.grid(row=hang_tuy_chon_1 + 1, column=0, sticky="w", pady=(4, 10))
        tk.Label(khung_khoang_thumb, text="Từ", font=FONT_NHAN, bg=MAU_THE,
                 fg=MAU_CHU_PHU).pack(side="left")
        self.o_tu_video_thumb = tk.Entry(khung_khoang_thumb, font=FONT_THUONG, width=5,
                                          bg=MAU_THE, fg=MAU_CHU_CHINH, relief="solid", bd=1,
                                          highlightbackground=MAU_VIEN, highlightthickness=1,
                                          justify="center")
        self.o_tu_video_thumb.pack(side="left", padx=(4, 10))
        tk.Label(khung_khoang_thumb, text="đến", font=FONT_NHAN, bg=MAU_THE,
                 fg=MAU_CHU_PHU).pack(side="left")
        self.o_den_video_thumb = tk.Entry(khung_khoang_thumb, font=FONT_THUONG, width=5,
                                           bg=MAU_THE, fg=MAU_CHU_CHINH, relief="solid", bd=1,
                                           highlightbackground=MAU_VIEN, highlightthickness=1,
                                           justify="center")
        self.o_den_video_thumb.pack(side="left", padx=(4, 0))

        self.bien_bo_qua_shorts_thumb = tk.BooleanVar(value=True)
        tk.Checkbutton(noi_dung, text="Bỏ qua video Shorts (≤ 60 giây)",
                        variable=self.bien_bo_qua_shorts_thumb,
                        bg=MAU_THE, fg=MAU_CHU_CHINH, font=FONT_THUONG,
                        activebackground=MAU_THE, selectcolor=MAU_THE,
                        anchor="w").grid(row=hang, column=0, columnspan=2, sticky="w", pady=(0, 12)); hang += 1

        # --- Tuỳ chỉnh màu sắc (Hue / Saturation / Value) ---
        self._nhan_muc(noi_dung, "Chỉnh màu ảnh (không cần đổi nếu muốn giữ nguyên)").grid(
            row=hang, column=0, columnspan=2, sticky="w", pady=(0, 6)); hang += 1

        khung_mau = tk.Frame(noi_dung, bg=MAU_THE)
        khung_mau.grid(row=hang, column=0, columnspan=2, sticky="w", pady=(0, 4)); hang += 1

        def _o_so_nho(cha, gia_tri_mac_dinh):
            o = tk.Entry(cha, font=FONT_THUONG, width=7, bg=MAU_THE, fg=MAU_CHU_CHINH,
                         relief="solid", bd=1, highlightbackground=MAU_VIEN, highlightthickness=1,
                         justify="center")
            o.insert(0, gia_tri_mac_dinh)
            return o

        tk.Label(khung_mau, text="Tông màu (Hue, độ, -360→360):", font=FONT_NHAN,
                 bg=MAU_THE, fg=MAU_CHU_PHU).grid(row=0, column=0, sticky="w", pady=3)
        self.o_hue = _o_so_nho(khung_mau, "0")
        self.o_hue.grid(row=0, column=1, sticky="w", padx=(8, 0))

        tk.Label(khung_mau, text="Độ bão hoà (Saturation, %, -100→100):", font=FONT_NHAN,
                 bg=MAU_THE, fg=MAU_CHU_PHU).grid(row=1, column=0, sticky="w", pady=3)
        self.o_saturation = _o_so_nho(khung_mau, "0")
        self.o_saturation.grid(row=1, column=1, sticky="w", padx=(8, 0))

        tk.Label(khung_mau, text="Độ sáng (Value, %, -100→100):", font=FONT_NHAN,
                 bg=MAU_THE, fg=MAU_CHU_PHU).grid(row=2, column=0, sticky="w", pady=3)
        self.o_value = _o_so_nho(khung_mau, "0")
        self.o_value.grid(row=2, column=1, sticky="w", padx=(8, 0))

        noi_dung.columnconfigure(0, weight=1)

        # --- Nút hành động (cố định, không cuộn) ---
        khung_co_dinh = tk.Frame(tab_cha, bg=MAU_NEN)
        khung_co_dinh.grid(row=1, column=0, sticky="ew", pady=(10, 12))

        khung_nut = tk.Frame(khung_co_dinh, bg=MAU_NEN)
        khung_nut.pack(fill="x", pady=(0, 8))
        self.nut_dem_thumb = NutTrangTron(khung_nut, text="1) Đếm & quét file đã tải",
                                           command=self._bat_dau_dem_thumbnail)
        self.nut_dem_thumb.pack(side="left")
        self.nut_tai_thumb = NutDen(khung_nut, text="2) Bắt đầu tải Thumbnails",
                                     command=self._bat_dau_tai_thumbnail, state="disabled")
        self.nut_tai_thumb.pack(side="left", padx=(10, 0))
        self.nut_huy_thumb = NutCanhBao(khung_nut, text="✕ Huỷ", command=self._huy_tai_thumb,
                                        state="disabled")
        self.nut_huy_thumb.pack(side="left", padx=(10, 0))

        khung_trang_thai = tk.Frame(khung_co_dinh, bg=MAU_NEN)
        khung_trang_thai.pack(fill="x")
        self.diem_trang_thai_thumb = tk.Label(khung_trang_thai, text="●", font=("Segoe UI", 9),
                                               bg=MAU_NEN, fg=MAU_DIEM_TRANG_THAI_SAN_SANG)
        self.diem_trang_thai_thumb.pack(side="left")
        self.nhan_trang_thai_thumb = tk.Label(khung_trang_thai, text="Sẵn sàng.", font=FONT_NHAN,
                                               bg=MAU_NEN, fg=MAU_CHU_PHU, anchor="w")
        self.nhan_trang_thai_thumb.pack(side="left", padx=(4, 0))

    # ---------------- TIỆN ÍCH GIAO DIỆN (dùng chung cho cả 2 tab) ----------------

    @staticmethod
    def _ten_bien_mau(gia_tri_mau):
        """Trả về TÊN biến màu ngữ nghĩa (vd 'MAU_THANH_CONG') ứng với 1 giá trị màu
        hex hiện tại, để dùng làm tên tag ổn định. Đổi giao diện chỉ đổi GIÁ TRỊ hex
        của MAU_THANH_CONG/MAU_LOI/MAU_CHU_PHU, không đổi Ý NGHĨA của màu đó -> tag
        theo tên biến (không theo hex) thì khi dựng lại giao diện mới có thể tô lại
        đúng sắc thái mới cho đúng ý nghĩa cũ (thành công/lỗi/phụ)."""
        if gia_tri_mau == MAU_THANH_CONG:
            return "MAU_THANH_CONG"
        if gia_tri_mau == MAU_LOI:
            return "MAU_LOI"
        if gia_tri_mau == MAU_CHU_PHU:
            return "MAU_CHU_PHU"
        return None

    def _ghi_log(self, dong, mau=None):
        """An toàn khi gọi từ bất kỳ luồng nào -> luôn đẩy qua luồng chính của tkinter
        để hiện lên khung chữ. Đồng thời (ĐỘC LẬP, KHÔNG đợi qua luồng chính - ghi
        NGAY tại đây) phụ lục thêm dòng đó vào file log của lần chạy này (nếu tạo
        file thành công lúc mở app - xem self._duong_dan_file_log), có thêm giờ:phút:
        giây phía trước mỗi dòng (KHÔNG thêm giờ vào khung chữ hiển thị, chỉ file mới
        có, để khung chữ trên giao diện giữ nguyên như trước, không rối mắt)."""
        def cap_nhat():
            self.khung_log.configure(state="normal")
            if mau:
                ten_bien = self._ten_bien_mau(mau)
                the_tag = f"tag_{ten_bien}" if ten_bien else f"tag_{mau}"
                self.khung_log.tag_config(the_tag, foreground=mau)
                self.khung_log.insert("end", dong + "\n", the_tag)
            else:
                self.khung_log.insert("end", dong + "\n")
            self.khung_log.see("end")
            self.khung_log.configure(state="disabled")
        self.cua_so_goc.after(0, cap_nhat)

        if self._duong_dan_file_log:
            with self._khoa_file_log:
                try:
                    gio = time.strftime("%H:%M:%S")
                    with open(self._duong_dan_file_log, "a", encoding="utf-8") as f:
                        f.write(f"[{gio}] {dong}\n")
                except OSError:
                    pass  # ghi file lỗi (đĩa đầy, mất quyền giữa chừng...) -> bỏ qua,
                          # KHÔNG được làm ảnh hưởng tới phần hiện log lên giao diện

    def _dat_trang_thai(self, chu, mau_diem=None):
        """Cập nhật dòng trạng thái ngắn gọn, kèm đổi màu chấm tròn phía trước để
        nhìn thoáng qua cũng biết ngay chương trình đang ở tình trạng nào."""
        def cap_nhat():
            self.nhan_trang_thai.configure(text=chu)
            if mau_diem:
                self.diem_trang_thai.configure(fg=mau_diem)
        self.cua_so_goc.after(0, cap_nhat)

    def _chon_file_ytdlp(self):
        duong_dan = filedialog.askopenfilename(title="Chọn file yt-dlp.exe",
                                                filetypes=[("Executable", "*.exe"), ("Tất cả", "*.*")])
        if duong_dan:
            self.o_ytdlp.delete(0, "end")
            self.o_ytdlp.insert(0, duong_dan)

    def _chon_thu_muc(self):
        duong_dan = filedialog.askdirectory(title="Chọn thư mục lưu video")
        if duong_dan:
            self.o_thu_muc.delete(0, "end")
            self.o_thu_muc.insert(0, duong_dan)

    def _kiem_tra_cap_nhat_ytdlp(self):
        self.nut_cap_nhat_ytdlp.configure(state="disabled")
        self._ghi_log("\nĐang kiểm tra cập nhật yt-dlp...")

        def chay_nen():
            try:
                ket_qua = core.tu_dong_cap_nhat_ytdlp(bao_tien_trinh=lambda m: self._ghi_log(f"  {m}"))
            except Exception as loi:
                ket_qua = {"thanh_cong": False, "ghi_chu": f"Lỗi không mong muốn: {loi}"}

            def cap_nhat_giao_dien():
                self.nut_cap_nhat_ytdlp.configure(state="normal")
                mau = MAU_THANH_CONG if ket_qua["thanh_cong"] else MAU_LOI
                self._ghi_log(f"  {ket_qua['ghi_chu']}", mau=mau)
            self.cua_so_goc.after(0, cap_nhat_giao_dien)

        threading.Thread(target=chay_nen, daemon=True).start()

    def _chon_thu_muc_thumb(self):
        duong_dan = filedialog.askdirectory(title="Chọn thư mục lưu thumbnails")
        if duong_dan:
            self.o_thu_muc_thumb.delete(0, "end")
            self.o_thu_muc_thumb.insert(0, duong_dan)

    def _luu_api_key(self):
        api_key = thumb_core._lam_sach_api_key(self.o_api_key.get())
        if not api_key:
            messagebox.showwarning("Thiếu API key", "Vui lòng nhập API key trước khi lưu.")
            return
        if thumb_core.luu_api_key(api_key):
            messagebox.showinfo("Đã lưu", "Đã lưu API key. Lần sau mở chương trình sẽ tự điền sẵn.")
            self._ghi_log("Đã lưu YouTube Data API key vào file cấu hình.", mau=MAU_THANH_CONG)
        else:
            messagebox.showerror("Lỗi", "Không thể lưu API key vào file cấu hình.")

    def _tu_dong_lay_api_key(self):
        """Bấm '🪄 Tự động lấy': chương trình tự làm phần lớn các bước tạo API Key
        trên Google Cloud (tạo Project, bật YouTube Data API v3, tạo + giới hạn Key)
        qua Google Cloud CLI (gcloud). VẪN CẦN bạn đăng nhập Google 1 lần qua trình
        duyệt khi được yêu cầu - đây là quy định bảo mật của Google, không phần mềm
        nào bỏ qua được (kể cả phần mềm chính chủ của Google)."""
        canh_bao = (
            "Chương trình sẽ tự động:\n"
            "  1) Cài Google Cloud CLI nếu máy chưa có (~150-300MB)\n"
            "  2) Mở trình duyệt để bạn ĐĂNG NHẬP GOOGLE (bắt buộc - yêu cầu bảo mật "
            "của Google, không thể bỏ qua)\n"
            "  3) Tự tạo 1 Google Cloud Project mới\n"
            "  4) Tự bật YouTube Data API v3 cho project đó\n"
            "  5) Tự tạo + giới hạn phạm vi API Key, rồi điền thẳng vào ô bên trên\n\n"
            "Lưu ý: nếu tài khoản Google của bạn chưa liên kết phương thức thanh toán, "
            "Google có thể yêu cầu liên kết trước khi bật được API (vẫn HOÀN TOÀN MIỄN "
            "PHÍ trong hạn mức, chỉ cần thẻ để xác minh) - chương trình sẽ báo rõ nếu "
            "gặp phải, không tự vượt qua được bước này.\n\n"
            "Bạn có muốn tiếp tục không?"
        )
        if not messagebox.askyesno("Tự động lấy API Key", canh_bao):
            return

        self.nut_tu_dong_lay_key.configure(state="disabled")
        self._ghi_log("\n🪄 Đang tự động lấy YouTube Data API Key...", mau=MAU_THANH_CONG)

        def chay_nen():
            try:
                api_key = thumb_core.tu_dong_lay_api_key(
                    bao_tien_trinh=lambda d: self._ghi_log(f"  {d}"))
            except Exception as loi:
                self._ghi_log(f"  Lỗi không mong muốn: {loi}", mau=MAU_LOI)
                api_key = None

            def cap_nhat_giao_dien():
                self.nut_tu_dong_lay_key.configure(state="normal")
                if api_key:
                    self.o_api_key.delete(0, "end")
                    self.o_api_key.insert(0, api_key)
                    thumb_core.luu_api_key(api_key)
                    messagebox.showinfo("Thành công",
                                         "Đã tự động lấy và điền API Key vào ô bên trên "
                                         "(đã lưu sẵn, không cần bấm 'Lưu key' nữa).")
                else:
                    messagebox.showerror("Không thành công",
                                          "Không tự lấy được API Key. Xem chi tiết lỗi trong "
                                          "khung Thông tin, hoặc lấy thủ công tại Google Cloud "
                                          "Console.")
            self.cua_so_goc.after(0, cap_nhat_giao_dien)

        threading.Thread(target=chay_nen, daemon=True).start()

    def _tu_dong_tim_ytdlp_khi_khoi_dong(self):
        self._ghi_log("Đang tự động dò tìm yt-dlp trên máy...")

        def chay_nen():
          try:
            duong_dan = core.tu_dong_tim_ytdlp()
            if duong_dan:
                core.DUONG_DAN_YTDLP = duong_dan

                def cap_nhat():
                    self.o_ytdlp.delete(0, "end")
                    self.o_ytdlp.insert(0, duong_dan)
                self.cua_so_goc.after(0, cap_nhat)
                self._ghi_log(f"  Đã tìm thấy yt-dlp tại: {duong_dan}", mau=MAU_THANH_CONG)
            else:
                self._ghi_log("  Không tự tìm thấy yt-dlp. Hãy bấm 'Chọn file...' để chỉ định thủ công.",
                              mau=MAU_LOI)

            # Nối tiếp: tự dò tìm ffmpeg (dùng để ghép audio+video). Thiếu ffmpeg là
            # nguyên nhân phổ biến khiến 1 số video tải về BỊ MẤT ÂM THANH.
            duong_dan_ffmpeg = core.tu_dong_tim_ffmpeg()
            if duong_dan_ffmpeg:
                core.DUONG_DAN_FFMPEG = duong_dan_ffmpeg
                self._ghi_log(f"  Đã tìm thấy ffmpeg tại: {duong_dan_ffmpeg}", mau=MAU_THANH_CONG)
            else:
                self._ghi_log("  Không tìm thấy ffmpeg trên máy - đang thử TỰ ĐỘNG TẢI VỀ...",
                              mau=MAU_LOI)
                duong_dan_ffmpeg_tai_ve, _ = core.tu_dong_tai_ffmpeg(bao_tien_trinh=self._ghi_log)
                if duong_dan_ffmpeg_tai_ve:
                    core.DUONG_DAN_FFMPEG = duong_dan_ffmpeg_tai_ve
                else:
                    self._ghi_log("  KHÔNG tự tải được ffmpeg (có thể do không có mạng). Một số "
                                  "video (cần ghép audio+video) có thể bị tải THIẾU ÂM THANH. Hãy "
                                  "cài ffmpeg thủ công rồi khởi động lại chương trình.", mau=MAU_LOI)

            # Nối tiếp: kiểm tra ffprobe (dùng để xác nhận chất lượng file thật sau khi
            # tải). Báo ngay lúc khởi động thay vì để cảnh báo lặp lại trên từng file.
            if core.ffprobe_kha_dung():
                self._ghi_log("  Đã tìm thấy ffprobe (dùng để kiểm tra chất lượng file).",
                              mau=MAU_THANH_CONG)
            else:
                self._ghi_log("  Không tìm thấy ffprobe trên máy - đang thử TỰ ĐỘNG TẢI VỀ...",
                              mau=MAU_LOI)
                duong_dan_ffmpeg_tai_ve2, _ = core.tu_dong_tai_ffmpeg(bao_tien_trinh=self._ghi_log)
                if duong_dan_ffmpeg_tai_ve2 and not core.DUONG_DAN_FFMPEG:
                    core.DUONG_DAN_FFMPEG = duong_dan_ffmpeg_tai_ve2
                if core.ffprobe_kha_dung():
                    self._ghi_log("  Đã tự động tải xong ffprobe.", mau=MAU_THANH_CONG)
                else:
                    self._ghi_log(
                        "  KHÔNG tự tải được ffprobe. Chương trình vẫn tải video bình thường, "
                        "nhưng sẽ KHÔNG kiểm tra được chất lượng thật của file sau khi tải (bỏ "
                        "qua bước xác nhận độ phân giải). Hãy kiểm tra kết nối mạng, hoặc tải "
                        "thủ công bộ ffmpeg đầy đủ (gyan.dev/BtbN) rồi đặt ffprobe.exe chung "
                        "thư mục với ffmpeg.exe hiện có.", mau=MAU_LOI)

            # Nối tiếp: chỉ còn nhắc (không tự cài) nếu thiếu 'deno' trong PATH -
            # đã bỏ hẳn máy chủ PO Token cục bộ (bgutil-pot.exe)/plugin liên quan,
            # lệnh tải giờ áp cứng "--extractor-args youtube:po_token_source=auto"
            # giống hệt lệnh yt-dlp chạy tay, không cần cài/khởi động gì thêm.
            core._canh_bao_neu_thieu_deno(bao_tien_trinh=self._ghi_log)

            # Nối tiếp: tự kiểm tra/cài các thư viện cần cho tab Thumbnails
            # (requests, Pillow, numpy, google-api-python-client).
            self._ghi_log("Đang kiểm tra thư viện cho tính năng Thumbnails...")
            if thumb_core._dam_bao_co_thu_vien(bao_tien_trinh=self._ghi_log):
                self._ghi_log("  Đã sẵn sàng tính năng tải Thumbnails.", mau=MAU_THANH_CONG)
            else:
                self._ghi_log("  Thiếu thư viện cho tab Thumbnails (xem lỗi ở trên).", mau=MAU_LOI)
          finally:
            # TẤT CẢ các bước chuẩn bị đã xong (dù có bước nào lỗi/thiếu, hay thậm chí
            # có ngoại lệ bất ngờ nào rơi ra giữa chừng đi nữa) -> LUÔN mở khoá lại cửa
            # sổ chính, tuyệt đối không được để người dùng bị khoá cứng vĩnh viễn chỉ vì
            # 1 bước chuẩn bị bị lỗi.
            self.cua_so_goc.after(0, self._dong_man_hinh_dang_cai_dat)

        threading.Thread(target=chay_nen, daemon=True).start()

    # ---------------- HÀNH ĐỘNG CHÍNH ----------------

    def _bat_dau_dem_va_quet(self):
        url_kenh = self.o_url.get().strip()
        thu_muc_luu_nhap = self.o_thu_muc.get().strip()
        duong_dan_ytdlp = self.o_ytdlp.get().strip()

        if not url_kenh:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập URL kênh.")
            return
        if not thu_muc_luu_nhap:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn/nhập thư mục lưu.")
            return
        if duong_dan_ytdlp:
            core.DUONG_DAN_YTDLP = duong_dan_ytdlp

        if core.la_duong_dan_day_du(thu_muc_luu_nhap):
            thu_muc_luu = thu_muc_luu_nhap
        else:
            thu_muc_luu = os.path.join(core.O_DIA_MAC_DINH, thu_muc_luu_nhap)
            self._ghi_log(f"(Chỉ nhập tên, sẽ dùng thư mục: {thu_muc_luu})")

        try:
            os.makedirs(thu_muc_luu, exist_ok=True)
        except OSError as loi:
            messagebox.showerror("Lỗi thư mục", f"Không thể tạo thư mục:\n{loi}")
            return

        self.thu_muc_luu_da_chon = thu_muc_luu
        self.nut_dem.configure(state="disabled")
        self.nut_tai.configure(state="disabled")
        self._dat_trang_thai("Đang đếm video...", mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)
        self._ghi_log("\n" + "-" * 50)

        # Tự chuyển URL kênh (@handle, /channel/, /c/, /user/...) sang ĐÚNG 1 URL
        # playlist "Uploads" (list=UU...) - tránh lỗi yt-dlp tách kênh thành nhiều
        # playlist con theo tab (Videos/Shorts/Live), khiến --playlist-items N áp
        # NHẦM lên từng playlist con thay vì đúng 1 chuỗi số liên tục toàn kênh (xem
        # core.chuan_hoa_url_kenh_thanh_playlist_uploads để biết chi tiết chẩn đoán).
        api_key_hien_tai = thumb_core._lam_sach_api_key(self.o_api_key.get())
        url_kenh_moi, ghi_chu_loi = core.chuan_hoa_url_kenh_thanh_playlist_uploads(
            url_kenh, api_key_hien_tai)
        if url_kenh_moi != url_kenh:
            self._ghi_log(f"  (Đã tự chuyển URL kênh sang playlist Uploads: {url_kenh_moi})")
            url_kenh = url_kenh_moi
            self.o_url.delete(0, "end")
            self.o_url.insert(0, url_kenh)
        elif ghi_chu_loi:
            self._ghi_log(f"  ⚠ {ghi_chu_loi}", mau=MAU_LOI)

        self._ghi_log("Đang đếm tổng số video của kênh, vui lòng chờ...")

        tai_shorts = self.bien_shorts.get()

        # Đọc khoảng video người dùng muốn tải (để trống = None = không giới hạn).
        try:
            tu_nhap = self.o_tu_video.get().strip()
            den_nhap = self.o_den_video.get().strip()
            tu_video = int(tu_nhap) if tu_nhap else None
            den_video = int(den_nhap) if den_nhap else None
        except ValueError:
            messagebox.showwarning(
                "Sai giá trị",
                "'Từ video số' / 'đến video số' phải là số nguyên dương (hoặc để trống)."
            )
            return

        def chay_nen():
            tong_so_video = core.dem_tong_so_video(url_kenh, tai_shorts)
            if tong_so_video is None:
                self._ghi_log("  LỖI: Không đếm được video. Kiểm tra lại URL kênh hoặc đường dẫn yt-dlp.",
                              mau=MAU_LOI)
                self._dat_trang_thai("Lỗi khi đếm video.", mau_diem=MAU_DIEM_TRANG_THAI_LOI)
                self.cua_so_goc.after(0, lambda: self.nut_dem.configure(state="normal"))
                return

            try:
                tu, den = core.xac_dinh_khoang_video(tong_so_video, tu_video, den_video)
            except ValueError as loi:
                self._ghi_log(f"  LỖI: {loi}", mau=MAU_LOI)
                self._dat_trang_thai("Khoảng video không hợp lệ.", mau_diem=MAU_DIEM_TRANG_THAI_LOI)
                self.cua_so_goc.after(0, lambda: self.nut_dem.configure(state="normal"))
                return

            do_rong_dem = core.tinh_do_rong_dem(tong_so_video)
            stt_da_co = core.quet_stt_da_co(thu_muc_luu)
            danh_sach_thieu = [i for i in range(tu, den + 1) if i not in stt_da_co]

            self._ghi_log(f"  Tổng số video      : {tong_so_video}")
            if tu_video or den_video:
                self._ghi_log(f"  Khoảng đã chọn     : từ video {tu} đến video {den}"
                               f" ({den - tu + 1} video)")
            self._ghi_log(f"  Đã có (bỏ qua)     : {len(stt_da_co)}")
            self._ghi_log(f"  Còn thiếu cần tải  : {len(danh_sach_thieu)}")

            self.tong_so_video = tong_so_video
            self.danh_sach_thieu = danh_sach_thieu
            self.do_rong_dem = do_rong_dem

            def cap_nhat_giao_dien():
                self.nut_dem.configure(state="normal")
                if danh_sach_thieu:
                    self.nut_tai.configure(state="normal")
                    self._dat_trang_thai(f"Còn {len(danh_sach_thieu)} video cần tải.",
                                          mau_diem=MAU_DIEM_TRANG_THAI_SAN_SANG)
                    self._ghi_log("-> Bấm '2) Bắt đầu tải' để tiếp tục.", mau=MAU_THANH_CONG)
                else:
                    self.nut_tai.configure(state="disabled")
                    self._dat_trang_thai("Đã tải đầy đủ.", mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)
                    self._ghi_log("-> Đã tải đầy đủ, không còn video nào cần tải thêm!", mau=MAU_THANH_CONG)

            self.cua_so_goc.after(0, cap_nhat_giao_dien)

        threading.Thread(target=chay_nen, daemon=True).start()

    def _bat_dau_tai(self):
        if not self.danh_sach_thieu:
            messagebox.showinfo("Không có gì để tải", "Không còn video nào cần tải.")
            return

        url_kenh = self.o_url.get().strip()
        tai_shorts = self.bien_shorts.get()
        thu_muc_luu = self.thu_muc_luu_da_chon
        chi_tai_am_thanh = self.bien_chi_am_thanh.get()

        gioi_han_chat_luong = None
        nhan_chat_luong = "Chỉ âm thanh (MP3)"
        if not chi_tai_am_thanh:
            chi_so_chat_luong = self.o_chat_luong.current()
            if chi_so_chat_luong < 0:
                messagebox.showwarning("Chưa chọn chất lượng",
                                        "Vui lòng chọn chất lượng video trước khi tải.")
                return
            gioi_han_chat_luong = core.DANH_SACH_CHAT_LUONG[chi_so_chat_luong][0]
            nhan_chat_luong = self._nhan_hien_thi_chat_luong[chi_so_chat_luong]

        nhung_phu_de = self.bien_nhung_phu_de.get()
        nhung_metadata = self.bien_nhung_metadata.get()
        chi_so_kieu_ten = self.o_kieu_ten_file.current()
        kieu_ten_file = self._ma_kieu_ten_file[chi_so_kieu_ten] if chi_so_kieu_ten >= 0 else "mac_dinh"
        dung_cookie = self.bien_dung_cookie.get()

        danh_sach_theo_luong = core.chia_theo_luong(self.danh_sach_thieu, SO_LUONG_CO_DINH)

        xac_nhan = messagebox.askyesno(
            "Xác nhận",
            f"Tải {len(self.danh_sach_thieu)} video còn thiếu?"
        )
        if not xac_nhan:
            return

        # Ghi nhớ thông tin luồng của đợt tải này để "Tiếp tục" sau này có thể
        # khởi động lại đúng cùng cách chia luồng (dùng khi Tạm dừng rồi Tiếp tục)
        self._thong_tin_dot_tai = dict(url_kenh=url_kenh, tai_shorts=tai_shorts,
                                        thu_muc_luu=thu_muc_luu,
                                        gioi_han_chat_luong=gioi_han_chat_luong,
                                        chi_tai_am_thanh=chi_tai_am_thanh,
                                        nhung_phu_de=nhung_phu_de,
                                        nhung_metadata=nhung_metadata,
                                        kieu_ten_file=kieu_ten_file,
                                        dung_cookie=dung_cookie)
        self._danh_sach_stt_theo_luong_dot_nay = danh_sach_theo_luong

        # Đặt lại bộ đếm tiến độ cho đợt tải này
        with self._khoa_tien_do:
            self._so_video_can_tai_dot_nay = len(self.danh_sach_thieu)
            self._so_video_da_xong_dot_nay = 0
        self._dang_tam_dung = False

        self.nut_dem.configure(state="disabled")
        self.nut_tai.configure(state="disabled")
        self.nut_tam_dung.configure(state="normal", text="⏸ Tạm dừng")
        self._dat_trang_thai(f"Đang tải... (0/{self._so_video_can_tai_dot_nay} video)",
                              mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)
        ghi_chu_cookie = "; MỌI video sẽ dùng cookie ngay từ đầu" if dung_cookie else ""
        self._ghi_log(f"\nĐang chạy ngầm {len(danh_sach_theo_luong)} luồng để tải song song "
                       f"{len(self.danh_sach_thieu)} video còn thiếu "
                       f"(chất lượng: {nhan_chat_luong}; mỗi video tải xong sẽ được kiểm tra chất "
                       f"lượng ngay{ghi_chu_cookie})...")

        self._khoi_dong_cac_tien_trinh(danh_sach_theo_luong)

    def _khoi_dong_cac_tien_trinh(self, danh_sach_theo_luong):
        """Khởi động (hoặc khởi động LẠI sau khi Tạm dừng) các LUỒNG (thread) tải
        ngầm, mỗi luồng tự lặp tải LẦN LƯỢT từng video một trong phần được giao (xem
        _luong_tai_video) - tải xong 1 video là kiểm tra chất lượng ngay, không đợi
        tải hết cả phần mới kiểm tra. Dùng chung cho cả lúc bấm '2) Bắt đầu tải' lẫn
        lúc bấm '▶ Tiếp tục'."""
        with self._khoa_tien_do:
            self._so_tien_trinh_dang_chay = len(danh_sach_theo_luong)
            self._tien_trinh_hien_tai_theo_luong = {}
            self._the_he_tai_dot_nay += 1
            the_he_dot_nay = self._the_he_tai_dot_nay

        for idx, danh_sach_stt in enumerate(danh_sach_theo_luong, start=1):
            self._ghi_log(f"  Đã khởi động luồng {idx} ({len(danh_sach_stt)} video)")
            threading.Thread(target=self._luong_tai_video,
                              args=(danh_sach_stt, idx, the_he_dot_nay),
                              daemon=True).start()

    def _luong_tai_video(self, danh_sach_stt, idx_luong, the_he_dot_nay):
        """Chạy trong 1 luồng nền riêng: lặp qua TỪNG video một trong danh_sach_stt
        được giao, tải xong video nào là kiểm tra chất lượng video đó luôn (xem
        _tai_va_kiem_tra_1_video), rồi mới sang video kế tiếp."""
        info = dict(self._thong_tin_dot_tai)
        do_rong_dem = self.do_rong_dem
        chi_tai_am_thanh = info.get("chi_tai_am_thanh", False)
        dung_cookie = info.get("dung_cookie", False)
        target_height = None if chi_tai_am_thanh else core.clamp_chat_luong(
            info.get("gioi_han_chat_luong", core.GIOI_HAN_CHAT_LUONG))

        for stt in danh_sach_stt:
            with self._khoa_tien_do:
                if the_he_dot_nay != self._the_he_tai_dot_nay or self._dang_tam_dung:
                    break

            ket_qua = self._tai_va_kiem_tra_1_video(
                stt, idx_luong, the_he_dot_nay, info, do_rong_dem,
                chi_tai_am_thanh, dung_cookie, target_height)
            if ket_qua is None:
                break  # bị Tạm dừng giữa chừng - dừng hẳn luồng này, không tính vào bộ đếm

            with self._khoa_tien_do:
                neu_dung_dot = (the_he_dot_nay == self._the_he_tai_dot_nay)
                if neu_dung_dot:
                    self._so_video_da_xong_dot_nay += 1
                da_xong = self._so_video_da_xong_dot_nay
                can_tai = self._so_video_can_tai_dot_nay
            if neu_dung_dot:
                self._dat_trang_thai(f"Đang tải... ({da_xong}/{can_tai} video)")

        self._danh_dau_1_tien_trinh_ket_thuc(the_he_dot_nay)

    def _chay_lenh_va_lay_ket_qua(self, lenh, idx_luong, the_he_dot_nay, nguon_cookie=None):
        """TÁCH RIÊNG từ _chay_1_tien_trinh_video: chạy 1 lệnh yt-dlp ĐÃ XÂY SẴN (lenh,
        dạng list), ĐỢI tới khi xong hẳn, rồi phân tích đầu ra trả về dict
        {"thanh_cong": bool, "tieu_de": str, "loi": str}. Trả về None nếu bị NGƯỜI
        DÙNG chủ động Tạm dừng giữa chừng.
        Tách thành hàm riêng để DÙNG CHUNG cho cả lượt thử RÚT GỌN đầu tiên (core.
        xay_dung_lenh_don_gian) LẪN lượt thử ĐẦY ĐỦ như trước nay (core.xay_dung_lenh)
        - xem _chay_1_tien_trinh_video ngay dưới."""
        # THÊM (theo yêu cầu người dùng - xem TIEN_DO_VA_VIEC_CAN_LAM.md, mục "không
        # biết có phải dùng cookies để tải không"): khi CÓ dùng cookie, ghi rõ NGAY
        # trong log 1 dòng xác nhận cờ --cookies THẬT SỰ có trong lệnh gọi yt-dlp hay
        # không, kèm đường dẫn file cookie - để không phải đoán mò / tin suông rằng
        # tính năng cookie có hoạt động hay không. KHÔNG in cả lệnh đầy đủ (có thể dài,
        # gây rối log) - chỉ in đúng phần liên quan tới cookie.
        if nguon_cookie:
            try:
                idx_cookie = lenh.index("--cookies")
                self._ghi_log(f"    (dùng cookie: --cookies \"{lenh[idx_cookie + 1]}\")")
            except (ValueError, IndexError):
                try:
                    idx_cookie = lenh.index("--cookies-from-browser")
                    self._ghi_log(f"    (dùng cookie: --cookies-from-browser {lenh[idx_cookie + 1]})")
                except (ValueError, IndexError):
                    self._ghi_log("    ⚠ nguon_cookie được truyền vào nhưng KHÔNG thấy cờ "
                                  "--cookies/--cookies-from-browser trong lệnh yt-dlp - có "
                                  "thể là bug, cần rà lại core.xay_dung_lenh()/"
                                  "xay_dung_lenh_don_gian().", mau=MAU_LOI)
        try:
            tien_trinh = core.mo_tien_trinh_an(lenh)
        except FileNotFoundError:
            self.cua_so_goc.after(0, lambda: messagebox.showerror(
                "Lỗi", f"Không tìm thấy yt-dlp tại '{core.DUONG_DAN_YTDLP}'."))
            return {"thanh_cong": False, "tieu_de": ""}

        with self._khoa_tien_do:
            self._tien_trinh_hien_tai_theo_luong[idx_luong] = tien_trinh

        dau_ra, _ = tien_trinh.communicate()

        with self._khoa_tien_do:
            self._tien_trinh_hien_tai_theo_luong.pop(idx_luong, None)
            bi_dung_giua_chung = (the_he_dot_nay != self._the_he_tai_dot_nay) or self._dang_tam_dung

        if bi_dung_giua_chung:
            return None

        tieu_de = ""
        cac_dong_loi = []
        for dong in (dau_ra or "").splitlines():
            ket_qua = core.phan_tich_dong_tien_do(dong)
            if ket_qua and ket_qua[0] == "da_xong":
                tieu_de = ket_qua[2]
            elif core.la_dong_loi(dong):
                cac_dong_loi.append(dong.strip())
                self._ghi_log(f"  ✗ Luồng {idx_luong} lỗi: {dong.strip()}", mau=MAU_LOI)

        return {"thanh_cong": tien_trinh.returncode == 0, "tieu_de": tieu_de,
                "loi": "; ".join(cac_dong_loi)}

    def _chay_1_tien_trinh_video(self, info, stt, do_rong_dem, idx_luong, the_he_dot_nay,
                                  nguon_cookie=None, thu_lenh_rut_gon_truoc=False):
        """Chạy tiến trình yt-dlp tải ĐÚNG 1 video (stt), ĐỢI tới khi xong hẳn rồi trả
        về dict {"thanh_cong": bool, "tieu_de": str}.
        Trả về None nếu bị NGƯỜI DÙNG chủ động Tạm dừng giữa chừng.

        thu_lenh_rut_gon_truoc=True (CHỈ bật ở LƯỢT THỬ ĐẦU TIÊN của mỗi video - xem
        các nơi gọi trong _tai_va_kiem_tra_1_video/_tai_1_video_bang_cookie_khong_ytdlp,
        KHÔNG bật lại ở các lượt thử dự phòng sau đó): theo yêu cầu người dùng, THỬ
        TRƯỚC 1 lệnh yt-dlp RÚT GỌN (core.xay_dung_lenh_don_gian - dùng
        --extractor-args "youtube:po_token_source=auto", KHÔNG cần máy chủ PO Token
        cục bộ). Mọi thứ khác (thư mục lưu, link kênh, đường dẫn yt-dlp tự dò, chất
        lượng chọn từ giao diện, đánh số thứ tự file...) vẫn liên kết y hệt lượt tải
        đầy đủ. CHỈ khi lượt rút gọn này THẤT BẠI (yt-dlp thoát mã lỗi khác 0), hàm
        mới xây và chạy TIẾP lệnh ĐẦY ĐỦ (core.xay_dung_lenh, với toàn bộ chuỗi
        player_client dự phòng + máy chủ PO Token cục bộ) như trước nay - KHÔNG đổi
        gì ở phần đó."""
        if thu_lenh_rut_gon_truoc:
            lenh_rut_gon = core.xay_dung_lenh_don_gian(
                info["url_kenh"], info["tai_shorts"], info["thu_muc_luu"],
                do_rong_dem=do_rong_dem, playlist_items=str(stt),
                gioi_han_chat_luong=info.get("gioi_han_chat_luong", core.GIOI_HAN_CHAT_LUONG),
                chi_tai_am_thanh=info.get("chi_tai_am_thanh", False),
                nhung_phu_de=info.get("nhung_phu_de", False),
                nhung_metadata=info.get("nhung_metadata", False),
                kieu_ten_file=info.get("kieu_ten_file", "mac_dinh"),
                nguon_cookie=nguon_cookie,
            )
            ket_qua_rut_gon = self._chay_lenh_va_lay_ket_qua(
                lenh_rut_gon, idx_luong, the_he_dot_nay, nguon_cookie)
            if ket_qua_rut_gon is None:
                return None  # bị Tạm dừng giữa chừng
            if ket_qua_rut_gon.get("thanh_cong"):
                return ket_qua_rut_gon
            self._ghi_log("    (lệnh rút gọn [po_token_source=auto] không tải được - "
                          "chuyển sang chuỗi lệnh dự phòng đầy đủ...)")

        lenh = core.xay_dung_lenh(
            info["url_kenh"], info["tai_shorts"], info["thu_muc_luu"],
            do_rong_dem=do_rong_dem, playlist_items=str(stt),
            gioi_han_chat_luong=info.get("gioi_han_chat_luong", core.GIOI_HAN_CHAT_LUONG),
            chi_tai_am_thanh=info.get("chi_tai_am_thanh", False),
            nhung_phu_de=info.get("nhung_phu_de", False),
            nhung_metadata=info.get("nhung_metadata", False),
            kieu_ten_file=info.get("kieu_ten_file", "mac_dinh"),
            nguon_cookie=nguon_cookie,
        )
        return self._chay_lenh_va_lay_ket_qua(lenh, idx_luong, the_he_dot_nay, nguon_cookie)

    def _tai_1_video_bang_cookie_khong_ytdlp(self, info, stt, do_rong_dem, idx_luong,
                                              the_he_dot_nay, target_height, nguon_cookie):
        """Tải 1 video CÓ DÙNG cookie. Tên hàm giữ chữ "khong_ytdlp" vì lý do lịch sử
        (từng có 1 module rời tự gọi Innertube API để tránh dùng yt-dlp - đã xác định
        là SAI KIẾN TRÚC, không thể vá được, nên đã bỏ hẳn và xoá khỏi đĩa) nhưng bên
        trong giờ ĐƠN GIẢN LÀ gọi lại yt-dlp kèm cookie (core.xay_dung_lenh đã hỗ trợ
        sẵn nguon_cookie=("file", duong_dan)), y hệt _chay_1_tien_trinh_video() dùng
        cho lượt tải không-cookie - tận dụng nguyên vẹn hạ tầng PO Token + danh sách
        player_client dự phòng đã có sẵn.

        target_height không dùng tới (giữ lại tham số để chữ ký khớp với chỗ gọi ở
        _tai_va_kiem_tra_1_video - so sánh chất lượng thực tế sau khi tải vẫn do
        chính _tai_va_kiem_tra_1_video làm, không đổi)."""
        return self._chay_1_tien_trinh_video(
            info, stt, do_rong_dem, idx_luong, the_he_dot_nay, nguon_cookie=nguon_cookie,
            thu_lenh_rut_gon_truoc=True)

    def _thiet_lap_extension_cookie(self):
        """Gọi khi bấm nút "🧩 Thiết lập Extension đọc cookie". Hiện hướng dẫn từng
        bước (xem extension_cookie.huong_dan_thiet_lap), hỏi ID extension người
        dùng vừa copy từ chrome://extensions, rồi đăng ký Native Messaging Host
        (xem extension_cookie.cai_dat_native_messaging_host) - CHỈ ghi 1 file
        manifest JSON + 1 khoá registry HKCU, không đụng gì tới Chrome đang chạy,
        không cần khởi động lại Chrome/chương trình để có hiệu lực."""
        huong_dan = extension_cookie.huong_dan_thiet_lap()
        messagebox.showinfo("Thiết lập Extension đọc cookie", huong_dan)

        ma_extension = simpledialog.askstring(
            "ID Extension",
            "Dán ID extension vừa copy từ chrome://extensions (hoặc từ popup của "
            "extension) vào đây:",
            parent=self.cua_so_goc,
        )
        if not ma_extension:
            return  # người dùng bấm Huỷ - không làm gì thêm

        try:
            duong_dan_manifest = extension_cookie.cai_dat_native_messaging_host(ma_extension)
        except extension_cookie.LoiCaiDatNativeHost as loi:
            messagebox.showerror("Không thiết lập được", str(loi))
            return

        self._ghi_log(f"🧩 Đã đăng ký Extension đọc cookie (manifest: {duong_dan_manifest}).",
                      mau=MAU_THANH_CONG)
        messagebox.showinfo(
            "Đã thiết lập xong",
            "Đã đăng ký thành công! Giờ bạn có thể bấm icon extension trên thanh công cụ "
            "Chrome rồi bấm nút trong popup hiện ra để gửi cookie cho chương trình bất cứ "
            "lúc nào cần (không cần lặp lại bước thiết lập này nữa)."
        )

    def _khi_bat_tat_cookie(self):
        """Gọi ngay khi người dùng TÍCH/BỎ TÍCH ô cookie (công tắc DUY NHẤT - dùng
        hoặc không dùng). Khi đang tích: báo NGAY trong khung Thông tin có đọc được
        cookie hợp lệ hay không (không cần đợi tới lúc thực sự tải video mới biết),
        bằng cách đọc file cookie do Extension Chrome gửi sẵn - xem extension_cookie.py.
        Chỉ đọc 1 file trên đĩa, không mở thêm tiến trình/cửa sổ nào. Kết quả được
        cache lại (self._nguon_cookie_hoat_dong) nên nếu đã biết rồi (từ lần tích
        trước) thì chỉ nhắc lại, không đọc lại file. Riêng các trường hợp "chưa có/
        chưa đăng nhập" KHÔNG được cache vĩnh viễn - tích/bỏ tích lại ô này sau khi
        gửi lại cookie qua popup extension sẽ tự kiểm tra lại."""
        if not self.bien_dung_cookie.get():
            return  # đang bỏ tích -> không cần làm gì

        with self._khoa_cookie:
            da_biet = self._nguon_cookie_hoat_dong

        if da_biet == "khong_co":
            self._ghi_log("🍪 (Đã kiểm tra trước đó) Không đọc được cookie đăng nhập YouTube.",
                          mau=MAU_LOI)
            return
        if da_biet:
            self._ghi_log("🍪 (Đã kiểm tra trước đó) Cookie đăng nhập YouTube sẵn sàng dùng.",
                          mau=MAU_THANH_CONG)
            return

        nguon_ext, trang_thai_ext = extension_cookie.lay_nguon_cookie_tu_extension()
        if trang_thai_ext == "ok":
            with self._khoa_cookie:
                self._nguon_cookie_hoat_dong = nguon_ext
            self._ghi_log("🍪 Đã có cookie do Extension gửi sẵn - sẽ dùng cho MỌI video khi tải.",
                          mau=MAU_THANH_CONG)
            return

        if trang_thai_ext == "chua_gui":
            self._ghi_log("🍪 Extension đọc cookie chưa gửi cookie lần nào. Bấm nút \"🧩 Thiết lập "
                          "Extension đọc cookie\" ở trên (nếu chưa làm), rồi mở popup extension "
                          "trong Chrome và bấm \"Gửi cookie cho VideoDownloader\".", mau=MAU_LOI)
        elif trang_thai_ext == "qua_cu":
            self._ghi_log("🍪 Cookie Extension gửi trước đó đã quá cũ - hãy mở lại popup extension "
                          "và bấm gửi lại.", mau=MAU_LOI)
        elif trang_thai_ext == "chua_dang_nhap":
            self._ghi_log("🍪 Extension đã gửi cookie nhưng chưa thấy đăng nhập YouTube/Google - "
                          "hãy đăng nhập trong Chrome rồi gửi lại qua popup extension.",
                          mau=MAU_LOI)

    @staticmethod
    def _la_loi_po_token(van_ban):
        """Nhận biết lỗi PO Token kiểu '[youtube+GetPOT] ...: The page needs to be
        reloaded' trong log yt-dlp - CHỈ còn dùng để GHI CHÚ THÊM cho người dùng
        trong dòng log lỗi cuối cùng (xem _tai_va_kiem_tra_1_video), KHÔNG còn kích
        hoạt lượt thử lại nào nữa (đã bỏ hẳn máy chủ PO Token cục bộ/danh sách
        player_client dự phòng - lệnh tải giờ chỉ có 1 kiểu duy nhất, áp cứng
        "--extractor-args youtube:po_token_source=auto"). Đã xác nhận qua test thực
        tế (video TVLzu8Kkr5k, uiici5S4ZgE) và các báo lỗi tương tự trên GitHub của
        yt-dlp (VD issue #17389, #17405): lỗi này thường do YouTube chặn/đổi cách xác
        thực ở tầng cao hơn, không phải do máy chủ PO Token cục bộ - nên thử lại bằng
        client khác cũng không chắc hết lỗi, không đáng giữ lại độ phức tạp đó nữa."""
        van_ban = (van_ban or "").lower()
        return "getpot" in van_ban or "needs to be reloaded" in van_ban

    def _lay_nguon_cookie_de_dung(self):
        """Trả về nguon_cookie (tuple ("file", duong_dan) sẵn sàng đưa THẲNG vào
        core.xay_dung_lenh) nếu Extension đã gửi sẵn cookie đăng nhập YouTube dùng
        được (xem extension_cookie.py), hoặc None nếu không (Extension chưa thiết
        lập/chưa gửi/gửi quá cũ/chưa đăng nhập). Việc đọc CHỈ diễn ra khi cần (kết
        quả nhớ lại dùng cho các video sau) - khoá _khoa_cookie đảm bảo chỉ 1 luồng
        đọc tại 1 thời điểm."""
        with self._khoa_cookie:
            if self._nguon_cookie_hoat_dong == "khong_co":
                return None
            if self._nguon_cookie_hoat_dong:
                return self._nguon_cookie_hoat_dong

            nguon_ext, trang_thai_ext = extension_cookie.lay_nguon_cookie_tu_extension()
            if trang_thai_ext == "ok":
                self._nguon_cookie_hoat_dong = nguon_ext
                self._ghi_log("  🍪 Đã có cookie do Extension gửi sẵn - dùng ngay.",
                              mau=MAU_THANH_CONG)
                return self._nguon_cookie_hoat_dong

            if trang_thai_ext in ("chua_gui", "qua_cu", "chua_dang_nhap"):
                thong_bao = {
                    "chua_gui": "Extension đọc cookie chưa gửi cookie lần nào.",
                    "qua_cu": "Cookie Extension gửi trước đó đã quá cũ.",
                    "chua_dang_nhap": "Extension đã gửi cookie nhưng chưa thấy đăng nhập YouTube.",
                }[trang_thai_ext]
                self._ghi_log(f"  🍪 {thong_bao} Hãy mở popup extension trong Chrome và bấm "
                              "\"Gửi cookie cho VideoDownloader\" rồi thử lại. Giữ nguyên video "
                              "này ở chất lượng hiện tại.", mau=MAU_LOI)
                return None  # KHÔNG cache "khong_co" - còn cơ hội gửi lại cookie rồi dùng sau

            self._nguon_cookie_hoat_dong = "khong_co"
            self._ghi_log("  🍪 Không đọc được cookie từ Extension.", mau=MAU_LOI)
            return None

    def _tai_va_kiem_tra_1_video(self, stt, idx_luong, the_he_dot_nay, info, do_rong_dem,
                                  chi_tai_am_thanh, dung_cookie, target_height):
        """Tải ĐÚNG 1 video rồi kiểm tra chất lượng NGAY (nếu không phải chế độ chỉ
        tải âm thanh).

        Cookie giờ là CÔNG TẮC DUY NHẤT (dung_cookie), không còn liên quan gì tới
        việc chất lượng có bị hạ hay không:
          - dung_cookie=True: dùng cookie NGAY TỪ LƯỢT TẢI ĐẦU TIÊN cho video này.
          - dung_cookie=False: KHÔNG bao giờ dùng cookie cho video này.
        Nếu chất lượng tải về sau đó vẫn thấp hơn mong muốn, chương trình CHỈ ghi log
        cảnh báo - KHÔNG còn tự động tải lại bằng cookie (dù đang TẮT hay đang BẬT cookie
        cũng vậy, vì cookie đã được quyết định dùng hay không NGAY TỪ ĐẦU rồi).

        Trả về True khi xử lý xong (dù đạt được chất lượng mong muốn hay không) - chỉ
        trả về None nếu bị Tạm dừng.

        ĐÃ BỎ (theo yêu cầu người dùng): bước "dò trước định dạng khả dụng" trước khi
        tải thật (từng gọi core.do_chat_luong_kha_dung) - lệnh dò trước này tốn thêm 1
        lượt gọi yt-dlp/video, khi chạy song song nhiều luồng cùng lúc dễ gây timeout/
        nghẽn mạng không cần thiết. Giờ tải thẳng ở mức chất lượng đã chọn, bộ lọc -f
        (core.tao_bo_loc_dinh_dang) tự động lấy mức cao nhất có sẵn không vượt quá mức
        đã chọn."""
        stt_hien_thi = str(stt).zfill(do_rong_dem)

        # Cookie là công tắc duy nhất: BẬT thì lấy cookie NGAY, dùng cho lượt tải đầu
        # tiên (và MỌI lượt tải lại của video này, VD lượt tải lại vì lỗi audio/video
        # tách rời ngay dưới đây) - không còn phụ thuộc vào việc chất lượng có bị hạ
        # hay không.
        nguon_cookie_ban_dau = None
        if dung_cookie:
            nguon_cookie_ban_dau = self._lay_nguon_cookie_de_dung()
            if nguon_cookie_ban_dau is None:
                self._ghi_log(f"  ⚠ [{stt_hien_thi}] Không có cookie khả dụng - tải bình thường "
                              "(không cookie).")

        self._ghi_log(f"  ⬇ [{stt_hien_thi}] Đang tải"
                       f"{' (kèm cookie ngay từ đầu, KHÔNG qua yt-dlp)' if nguon_cookie_ban_dau else ''}...")

        # QUAN TRỌNG: khi có cookie để dùng NGAY TỪ ĐẦU, KHÔNG gọi yt-dlp nữa - dùng
        # hẳn đường tải riêng (tai_khong_ytdlp) như đã thống nhất: yt-dlp chỉ còn giữ
        # vai trò "tải chính" cho lượt KHÔNG cần cookie. Không có cookie khả dụng thì
        # vẫn rơi về yt-dlp bình thường (không đổi hành vi cũ) - xem nhánh else dưới.
        if nguon_cookie_ban_dau is not None:
            ket_qua_tai = self._tai_1_video_bang_cookie_khong_ytdlp(
                info, stt, do_rong_dem, idx_luong, the_he_dot_nay,
                target_height, nguon_cookie_ban_dau)
        else:
            ket_qua_tai = self._chay_1_tien_trinh_video(
                info, stt, do_rong_dem, idx_luong, the_he_dot_nay, nguon_cookie=None,
                thu_lenh_rut_gon_truoc=True)
        if ket_qua_tai is None:
            return None

        # SỬA LỖI: trước đây báo "✓ Đã xong" ngay cả khi tải THẤT BẠI (chỉ dựa vào
        # có tiêu đề rút ra được hay không, mà tiêu đề rỗng lại tự lấy fallback
        # "video #N" trông giống như đã thành công) - khiến log gây hiểu lầm kiểu
        # "✓ Đã xong: video #5" ngay trước dòng "⚠ Không thấy file". Giờ kiểm tra
        # THẲNG mã thoát yt-dlp (thanh_cong) trước khi báo thành công.
        if not ket_qua_tai.get("thanh_cong"):
            loi_cuoi = ket_qua_tai.get("loi") or "(không rõ lỗi cụ thể, xem log yt-dlp ở trên)"
            if self._la_loi_po_token(loi_cuoi):
                loi_cuoi += (" — đây nhiều khả năng là YouTube đang chặn/đổi cách xác thực "
                             "(không phải lỗi cookie hay máy bạn, xem yt-dlp issue #17389/"
                             "#17405) - hãy thử bấm \"🔄 Cập nhật yt-dlp\" rồi thử lại sau.")
            self._ghi_log(f"  ✗ [{stt_hien_thi}] Tải THẤT BẠI: {loi_cuoi}", mau=MAU_LOI)
            return True  # coi như đã xử lý xong (dù thất bại) - lần quét sau sẽ tự phát hiện thiếu file

        thu_muc = info["thu_muc_luu"]
        # SỬA LỖI (rà lại khi chẩn đoán tiếp lỗi video 0451/0255/0452): trước đây dùng
        # tim_file_theo_stt() (khớp theo tiền tố, KHÔNG loại trừ file backup mồ côi có
        # đuôi ".backup_chat_luong" nếu lỡ còn sót từ 1 lượt chạy trước bị lỗi/tắt đột
        # ngột) - nếu file đó tồn tại, cac_file[0] có thể LẤY NHẦM file backup (cũ) làm
        # "file vừa tải xong", khiến toàn bộ bước kiểm tra audio/video + chiều cao ngay
        # dưới đây chẩn đoán SAI FILE. Đổi sang tim_file_thuc_te_theo_stt() để luôn chỉ
        # lấy đúng file media hiện hành, giống các bước so sánh sau khi tải bằng cookie.
        # SỬA LỖI MỚI (theo log người dùng báo: "✓ Đã xong: video #N" in ra XONG NGAY
        # LẬP TỨC bị theo sau bởi "⚠ Không thấy file sau khi tải" cho ĐÚNG video đó,
        # lặp lại ở nhiều video khác nhau trong cùng 1 lượt tải cả kênh): bước tìm file
        # này TRƯỚC ĐÂY nằm SAU dòng log "✓ Đã xong" (dựa thẳng vào thanh_cong =
        # tien_trinh.returncode == 0, xem _chay_1_tien_trinh_video) - nhưng khi video bị
        # "--match-filter !is_short & duration>60" loại bỏ (là Shorts, hoặc <=60 giây,
        # xem core.xay_dung_lenh - filter này LUÔN được thêm khi không bật tải Shorts),
        # yt-dlp ÂM THẦM BỎ QUA HẲN video đó NGAY TỪ BƯỚC LỌC - không phải lỗi (không có
        # dòng "ERROR:" nào để la_dong_loi() bắt được), nên tien_trinh.returncode vẫn =
        # 0 y hệt tải thành công thật. Vì bị lọc TRƯỚC KHI vào giai đoạn tải, 2 mốc
        # --print before_dl:/after_move: (nguồn DUY NHẤT cung cấp tieu_de) cũng KHÔNG
        # BAO GIỜ được in ra -> tieu_de rỗng, rơi vào fallback "video #{stt}" trông y
        # hệt 1 lượt tải thành công thật, khiến dòng "✓ Đã xong" bị in ra SAI ngay
        # trước khi kịp biết là không hề có file nào. Giờ chuyển bước tìm file lên
        # TRƯỚC dòng log "✓ Đã xong", để phân biệt rõ 2 trường hợp:
        #   - tieu_de rỗng (chưa từng qua before_dl/after_move) VÀ không thấy file ->
        #     GẦN NHƯ CHẮC CHẮN bị match-filter loại (Shorts/quá ngắn), KHÔNG PHẢI lỗi
        #     - báo đúng bản chất bằng 1 dòng riêng, KHÔNG tô đỏ, KHÔNG coi là "lỗi"
        #     (thử tải lại cũng vô ích vì video này sẽ luôn bị lọc y hệt mỗi lần).
        #   - CÓ tieu_de (nghĩa là đã thực sự đi qua before_dl, tức KHÔNG bị lọc) mà
        #     VẪN không thấy file -> đây mới đúng là lỗi thật (VD tải dở bị ngắt, ổ đĩa
        #     đầy...) - giữ NGUYÊN cảnh báo cũ như trước.
        cac_file = core.tim_file_thuc_te_theo_stt(thu_muc, stt, do_rong_dem)
        tieu_de_thuc = (ket_qua_tai.get("tieu_de") or "").strip()

        if not cac_file and not tieu_de_thuc:
            self._ghi_log(
                f"  ⏭ [{stt_hien_thi}] Bỏ qua: video này là Shorts hoặc có thời lượng "
                "<=60 giây nên bị bộ lọc loại (đang tắt tải Shorts) - KHÔNG phải lỗi, "
                "không cần tải lại.")
            return True

        tieu_de = tieu_de_thuc or f"video #{stt}"
        self._ghi_log(f"  ✓ [{stt_hien_thi}] Đã xong: {tieu_de}", mau=MAU_THANH_CONG)

        if chi_tai_am_thanh:
            if not cac_file:
                self._ghi_log(f"  ⚠ [{stt_hien_thi}] Không thấy file sau khi tải - có thể đã "
                              "lỗi, lần quét sau sẽ tự phát hiện lại.", mau=MAU_LOI)
            return True  # chế độ chỉ tải âm thanh -> không có luồng hình để kiểm tra

        if not cac_file:
            self._ghi_log(f"  ⚠ [{stt_hien_thi}] Không thấy file sau khi tải - có thể đã lỗi, "
                          "lần quét sau sẽ tự phát hiện lại.", mau=MAU_LOI)
            return True

        # --- Kiểm tra lỗi TÁCH RỜI audio/video (thiếu tiếng hẳn, hoặc lệch thời lượng
        # do ffmpeg ghép cắt cụt giữa chừng) - kiểm tra NGAY sau khi tải, TRƯỚC cả bước
        # so độ phân giải, vì đây là lỗi nghiêm trọng hơn (video câm) và nguyên nhân
        # khác hẳn (lỗi ghép audio/video cục bộ, không liên quan cookie/đăng nhập).
        bi_loi_av, ly_do_loi_av = core.kiem_tra_loi_tach_audio_video(cac_file[0], chi_tai_am_thanh)
        if bi_loi_av:
            self._ghi_log(f"  ⚠ [{stt_hien_thi}] Lỗi ghép audio/video: {ly_do_loi_av}. "
                          "Đang xoá và tải lại...", mau=MAU_LOI)
            core.xoa_file_theo_stt(thu_muc, stt, do_rong_dem)
            ket_qua_tai_av = self._chay_1_tien_trinh_video(
                info, stt, do_rong_dem, idx_luong, the_he_dot_nay, nguon_cookie=nguon_cookie_ban_dau)
            if ket_qua_tai_av is None:
                return None
            cac_file = core.tim_file_thuc_te_theo_stt(thu_muc, stt, do_rong_dem)  # (lý do: xem chú thích ở lượt gọi đầu tiên phía trên)
            if not cac_file:
                self._ghi_log(f"  ✗ [{stt_hien_thi}] Không thấy file sau khi tải lại.",
                              mau=MAU_LOI)
                return True
            bi_loi_av_2, ly_do_loi_av_2 = core.kiem_tra_loi_tach_audio_video(
                cac_file[0], chi_tai_am_thanh)
            if bi_loi_av_2:
                self._ghi_log(f"  ✗ [{stt_hien_thi}] Tải lại vẫn lỗi audio/video ({ly_do_loi_av_2}) "
                              "- có thể máy đang thiếu/lỗi ffmpeg, hoặc mạng không ổn định. "
                              "Giữ nguyên file này, cần kiểm tra thủ công.", mau=MAU_LOI)
            else:
                self._ghi_log(f"  ✓ [{stt_hien_thi}] Tải lại đã hết lỗi audio/video.",
                              mau=MAU_THANH_CONG)

        chieu_cao = core.lay_chieu_cao_video(cac_file[0])
        if chieu_cao is None:
            # "Không đọc được chiều cao" có 2 nguyên nhân rất khác nhau - (1) ffprobe
            # lỗi/thiếu thật (không thể kiểm tra được gì), và (2) file KHÔNG CÓ LUỒNG
            # HÌNH NÀO (chỉ có âm thanh). Phân biệt rõ: mất hẳn luồng hình -> coi như
            # chất lượng 0p để đi tiếp xuống bước cảnh báo "chưa đạt yêu cầu" ngay
            # dưới đây (không còn tự tải lại - xem đầu docstring hàm này).
            tt_video = core.lay_thong_tin_audio_video(cac_file[0])
            if tt_video is not None and not tt_video["co_video"]:
                chieu_cao = 0
                self._ghi_log(f"  ⚠ [{stt_hien_thi}] File tải về KHÔNG CÓ HÌNH (chỉ có âm thanh).",
                              mau=MAU_LOI)
            else:
                self._ghi_log(f"  ⚠ [{stt_hien_thi}] Không đọc được chất lượng file (ffprobe lỗi/"
                              "thiếu) - bỏ qua kiểm tra.")
                return True

        if chieu_cao >= target_height:
            return True  # đạt yêu cầu

        # Chất lượng thấp hơn mong muốn: chỉ CẢNH BÁO, không còn tự động tải lại bằng
        # cookie nữa - cookie giờ là công tắc quyết định NGAY TỪ ĐẦU (dung_cookie), một
        # video đã tải với đúng lựa chọn đó rồi thì không thử thêm cách nào khác nữa.
        if nguon_cookie_ban_dau is not None:
            self._ghi_log(f"  ⚠ [{stt_hien_thi}] Đã dùng cookie nhưng chỉ tải được {chieu_cao}p "
                          f"(mong muốn {target_height}p) - giữ nguyên, có thể video gốc không có "
                          "sẵn chất lượng cao hơn.", mau=MAU_LOI)
        else:
            self._ghi_log(f"  ↓ [{stt_hien_thi}] Chỉ tải được {chieu_cao}p (mong muốn "
                          f"{target_height}p) - giữ nguyên.", mau=MAU_LOI)
        return True

    def _danh_dau_1_tien_trinh_ket_thuc(self, the_he_dot_nay):
        """Gọi mỗi khi 1 trong các tiến trình tải ngầm kết thúc (xong, lỗi, hoặc bị
        NGƯỜI DÙNG chủ động dừng bằng nút Tạm dừng).
        Khi TẤT CẢ tiến trình đã kết thúc THẬT SỰ (không phải do bấm Tạm dừng) thì mới
        mở lại các nút và ghi thông báo tổng kết."""
        with self._khoa_tien_do:
            # Callback lỗi thời (từ 1 đợt tải CŨ trước khi Tạm dừng/Tiếp tục) -> bỏ
            # qua hoàn toàn, KHÔNG được trừ vào bộ đếm của đợt tải hiện tại.
            if the_he_dot_nay != self._the_he_tai_dot_nay:
                return
            self._so_tien_trinh_dang_chay -= 1
            da_xong_het = self._so_tien_trinh_dang_chay <= 0
            da_xong = self._so_video_da_xong_dot_nay
            can_tai = self._so_video_can_tai_dot_nay
            dang_tam_dung = self._dang_tam_dung

        if not da_xong_het or dang_tam_dung:
            # Chưa xong hết, HOẶC các tiến trình này kết thúc là do bị NGƯỜI DÙNG chủ
            # động dừng (nút Tạm dừng) chứ không phải tự tải xong -> không coi là
            # hoàn tất, không đụng vào giao diện (nút Tạm dừng đã được _tam_dung_tiep_tuc
            # tự cập nhật rồi).
            return

        def cap_nhat_giao_dien():
            self.nut_dem.configure(state="normal")
            self.nut_tai.configure(state="disabled")
            self.nut_tam_dung.configure(state="disabled", text="⏸ Tạm dừng")
            self._dat_trang_thai(f"Đã tải xong {da_xong}/{can_tai} video.",
                                  mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)
            messagebox.showinfo(
                "Đã tải xong",
                f"Đã tải xong {da_xong}/{can_tai} video vào thư mục:\n"
                f"{self._thong_tin_dot_tai.get('thu_muc_luu', '')}",
            )

        self.cua_so_goc.after(0, cap_nhat_giao_dien)
        self._ghi_log(f"Đã chạy xong tất cả các luồng tải ({da_xong}/{can_tai} video).",
                      mau=MAU_THANH_CONG)
        self._ghi_log("Nếu còn thiếu (do lỗi/mất mạng giữa chừng): bấm lại "
                      "'1) Đếm video & quét file đã tải' rồi '2) Bắt đầu tải' để tải tiếp phần còn thiếu.")

    def _tam_dung_tiep_tuc(self):
        """Bấm để DỪNG HẲN toàn bộ các tiến trình tải đang chạy ngầm (giải phóng file
        ngay lập tức - có thể xoá file đang tải dở nếu muốn), bấm lại lần nữa để
        KHỞI ĐỘNG LẠI đúng các phần còn thiếu (video đã tải xong rồi sẽ được yt-dlp
        tự bỏ qua, chỉ tải lại những video chưa xong / đã bị xoá file)."""
        if not self._dang_tam_dung:
            with self._khoa_tien_do:
                danh_sach = list(self._tien_trinh_hien_tai_theo_luong.values())
                self._dang_tam_dung = True  # đặt TRƯỚC khi dừng, để các luồng đọc log
                                             # biết đây là dừng chủ động, không phải xong

            self.nut_tam_dung.configure(state="disabled")
            so_thanh_cong = sum(1 for tt in danh_sach if core.dung_han_tien_trinh(tt))

            self.nut_tam_dung.configure(text="▶ Tiếp tục", state="normal")
            self._dat_trang_thai("Đã tạm dừng - có thể xoá file video đang tải dở nếu muốn.")
            self._ghi_log(f"⏸ Đã dừng hẳn {so_thanh_cong} tiến trình đang tải, file đang tải dở "
                          "ĐÃ ĐƯỢC GIẢI PHÓNG (không còn bị khoá) - có thể xoá đi nếu muốn tải lại "
                          "từ đầu video đó. Bấm '▶ Tiếp tục' để tải tiếp phần còn thiếu.",
                          mau=MAU_THANH_CONG)
        else:
            self._dang_tam_dung = False
            self.nut_tam_dung.configure(text="⏸ Tạm dừng")
            self._dat_trang_thai("Đang tải...")

            # QUAN TRỌNG: quét lại thư mục để loại bỏ những video ĐÃ tải xong hẳn
            # trước khi bị Tạm dừng, thay vì gửi lại y nguyên danh sách STT ban đầu.
            # Trước đây gửi lại nguyên danh sách cũ có thể khiến 1 tiến trình mới ghi
            # đè lên đúng file vừa tải dở (do yt-dlp ghi thẳng vào tên file cuối cùng
            # lúc đang tải/ghép) -> gây lỗi "tải nhiều lần / đè lên nhau".
            thu_muc_luu = self._thong_tin_dot_tai["thu_muc_luu"]
            stt_da_co_hien_tai = core.quet_stt_da_co(thu_muc_luu)
            danh_sach_con_thieu = [i for i in self.danh_sach_thieu if i not in stt_da_co_hien_tai]

            if not danh_sach_con_thieu:
                self._ghi_log("▶ Quét lại thấy đã tải đầy đủ, không còn video nào cần tải tiếp.",
                              mau=MAU_THANH_CONG)
                self.nut_tam_dung.configure(state="disabled", text="⏸ Tạm dừng")
                self._dat_trang_thai("Đã tải đầy đủ.")
                return

            danh_sach_theo_luong = core.chia_theo_luong(danh_sach_con_thieu, SO_LUONG_CO_DINH)
            self._danh_sach_stt_theo_luong_dot_nay = danh_sach_theo_luong

            self._ghi_log(f"▶ Đang khởi động lại để tải tiếp {len(danh_sach_con_thieu)} video "
                          "còn thiếu thật sự (đã quét lại thư mục)...", mau=MAU_THANH_CONG)
            self._khoi_dong_cac_tien_trinh(danh_sach_theo_luong)

    # ---------------- ĐÓNG CHƯƠNG TRÌNH (đảm bảo dừng hẳn mọi tiến trình nền) ----------------

    def _khi_dong_cua_so(self):
        """Được gọi khi người dùng bấm nút X để đóng cửa sổ.

        QUAN TRỌNG: nếu chỉ đóng cửa sổ giao diện (hành vi mặc định của Tkinter),
        các tiến trình yt-dlp/ffmpeg đang chạy NGẦM (khởi động bằng subprocess.Popen)
        sẽ KHÔNG tự động bị dừng theo - đây là tiến trình HỆ ĐIỀU HÀNH độc lập,
        Windows không tự dừng tiến trình con khi tiến trình cha thoát. Hậu quả:
        chúng vẫn tiếp tục tải/ghép file ngầm sau khi cửa sổ đã đóng, gây ra tình
        trạng file/thư mục báo "đang được dùng bởi chương trình khác" khi cố xoá
        hoặc di chuyển sau đó (VD thư mục "dist" khi đóng gói).

        Hàm này vì vậy sẽ: hỏi xác nhận nếu đang có video dở dang, DỪNG HẲN toàn bộ
        tiến trình tải đang chạy (giống hệt cách nút 'Tạm dừng' làm), rồi thoát HẲN
        tiến trình Python bằng os._exit thay vì chỉ destroy() cửa sổ - đảm bảo không
        còn luồng nền (thread) hay handle file nào sót lại sau khi chương trình đã
        đóng."""
        with self._khoa_tien_do:
            danh_sach_tien_trinh = list(self._tien_trinh_hien_tai_theo_luong.values())
            con_dang_tai = any(tt.poll() is None for tt in danh_sach_tien_trinh)

        if con_dang_tai:
            if not messagebox.askyesno(
                "Đang tải dở",
                "Vẫn còn video đang tải. Đóng chương trình sẽ DỪNG HẲN việc tải "
                "(có thể tải tiếp sau bằng cách quét lại).\nBạn có chắc muốn đóng không?",
            ):
                return  # Người dùng chọn "No" -> giữ nguyên cửa sổ, không đóng.

        # Báo hiệu cho luồng tải thumbnail (nếu đang chạy) dừng lại sớm.
        self._huy_tai_thumbnail = True

        # Dừng hẳn mọi tiến trình yt-dlp/ffmpeg đang chạy ngầm (nếu có).
        for tien_trinh in danh_sach_tien_trinh:
            core.dung_han_tien_trinh(tien_trinh)

        # (Đã bỏ bước dọn Chrome/CDP ở đây - cookie giờ lấy qua Extension, không
        # còn tự mở cửa sổ Chrome riêng nào để phải dọn nữa.)

        # (Đã bỏ hẳn máy chủ PO Token cục bộ (bgutil-pot.exe) - không còn tiến trình
        # nền nào cần dừng ở đây nữa.)

        # Chờ tối đa ~2 giây để CHẮC CHẮN các tiến trình vừa yêu cầu dừng ở trên đã
        # thật sự thoát hẳn (taskkill/kill chỉ GỬI yêu cầu dừng, hệ điều hành có thể
        # mất thêm chút thời gian mới nhả khoá file/thư mục) - tránh đúng tình trạng
        # "The action can't be completed because the folder or a file in it is open
        # in another program" nếu người dùng mở lại/xoá thư mục tải NGAY sau khi vừa
        # đóng chương trình.
        thoi_diem_bat_dau_cho = time.time()
        while time.time() - thoi_diem_bat_dau_cho < 2.0:
            if all(tt.poll() is not None for tt in danh_sach_tien_trinh):
                break
            time.sleep(0.1)

        try:
            self.cua_so_goc.destroy()
        except Exception:
            pass

        # Thoát HẲN tiến trình (không chỉ dừng vòng lặp giao diện) để chắc chắn
        # không còn luồng nền nào của CHÍNH chương trình này sót lại phía sau.
        os._exit(0)

    # ---------------- TAB THUMBNAILS ----------------

    def _doc_tuy_chon_so_thuc(self, o_nhap, ten_hien_thi, gia_tri_mac_dinh=0.0):
        """Đọc 1 ô nhập số thực (Hue/Saturation/Value), báo lỗi rõ ràng nếu gõ sai."""
        chuoi = o_nhap.get().strip()
        if not chuoi:
            return gia_tri_mac_dinh
        try:
            return float(chuoi)
        except ValueError:
            raise ValueError(f"'{ten_hien_thi}' phải là một con số (VD: 0, 30, -15).")

    def _bat_dau_dem_thumbnail(self):
        try:
            self._bat_dau_dem_thumbnail_that_su()
        except Exception as loi:
            # An toàn tuyệt đối: KHÔNG được để bất kỳ lỗi bất ngờ nào ở phần xử lý
            # ĐỒNG BỘ (trước khi vào luồng nền) trôi qua âm thầm - ở bản .exe đóng gói
            # (không có cửa sổ CMD) thì lỗi kiểu này vốn dĩ Tkinter sẽ nuốt mất, khiến
            # người dùng tưởng nhầm là bấm nút "không phản hồi" dù thực ra có lỗi.
            self._ghi_log(f"[Thumbnails] LỖI KHÔNG MONG MUỐN khi bấm nút: "
                          f"{type(loi).__name__}: {loi}", mau=MAU_LOI)
            messagebox.showerror("Lỗi không mong muốn", f"{type(loi).__name__}: {loi}")
            self.nut_dem_thumb.configure(state="normal")

    def _bat_dau_dem_thumbnail_that_su(self):
        """Bước '1) Đếm & quét file đã tải' của tab Thumbnails: dò kênh, lấy danh
        sách video trong khoảng đã chọn, rồi QUÉT LẠI thư mục lưu để loại bỏ những
        STT đã có sẵn file - y hệt cơ chế bên tab 'Tải video' (_bat_dau_dem_va_quet),
        chỉ khác ở chỗ danh sách còn thiếu lưu kèm luôn thông tin video (lấy từ API)
        để bước tải sau đó (2) không cần dò lại kênh lần nữa."""
        url_kenh = self.o_url_thumb.get().strip()
        thu_muc_luu_nhap = self.o_thu_muc_thumb.get().strip()
        api_key = thumb_core._lam_sach_api_key(self.o_api_key.get())

        if not url_kenh:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập link kênh YouTube.")
            return
        if not thu_muc_luu_nhap:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn/nhập thư mục lưu thumbnails.")
            return
        if not api_key:
            messagebox.showwarning(
                "Thiếu API key",
                "Vui lòng nhập YouTube Data API key rồi bấm 'Lưu key' (chỉ cần làm 1 lần)."
            )
            return

        try:
            tu_nhap_thumb = self.o_tu_video_thumb.get().strip()
            den_nhap_thumb = self.o_den_video_thumb.get().strip()
            tu_video_thumb = int(tu_nhap_thumb) if tu_nhap_thumb else 1
            den_video_thumb = int(den_nhap_thumb) if den_nhap_thumb else None
            if tu_video_thumb < 1 or (den_video_thumb is not None and den_video_thumb < tu_video_thumb):
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Sai giá trị",
                "'Từ' / 'đến' phải là số nguyên dương (hoặc để trống), và 'đến' phải "
                ">= 'Từ'."
            )
            return

        if core.la_duong_dan_day_du(thu_muc_luu_nhap):
            thu_muc_luu = thu_muc_luu_nhap
        else:
            thu_muc_luu = os.path.join(core.O_DIA_MAC_DINH, thu_muc_luu_nhap)
            self._ghi_log(f"[Thumbnails] (Chỉ nhập tên, sẽ dùng thư mục: {thu_muc_luu})")

        try:
            os.makedirs(thu_muc_luu, exist_ok=True)
        except OSError as loi:
            messagebox.showerror("Lỗi thư mục", f"Không thể tạo thư mục:\n{loi}")
            return

        # Lưu lại key luôn (tiện cho người dùng, khỏi phải nhớ bấm "Lưu key" riêng)
        thumb_core.luu_api_key(api_key)

        bo_qua_shorts = self.bien_bo_qua_shorts_thumb.get()

        self.nut_dem_thumb.configure(state="disabled")
        self.nut_tai_thumb.configure(state="disabled")
        self._dat_trang_thai_thumb("Đang tìm kênh...", mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)
        self._ghi_log("\n" + "-" * 50)
        self._ghi_log(f"[Thumbnails] Đang dò kênh: {url_kenh}")

        def mo_lai_nut_dem():
            self.cua_so_goc.after(0, lambda: self.nut_dem_thumb.configure(state="normal"))

        def chay_nen():
            try:
                # Đảm bảo chắc chắn các thư viện (requests, google-api-python-client...)
                # đã sẵn sàng TRƯỚC khi dùng - phòng trường hợp bấm nút này quá sớm lúc
                # app vừa mở, trong khi luồng kiểm tra thư viện lúc khởi động (chạy nối
                # tiếp SAU phần PO Token, có thể mất tới 30 giây) vẫn chưa kịp chạy xong.
                # Gọi lại ở đây không tốn kém gì nếu đã sẵn sàng từ trước (chỉ kiểm tra
                # import, không tải/cài lại).
                if not thumb_core._dam_bao_co_thu_vien(bao_tien_trinh=self._ghi_log):
                    self._ghi_log("[Thumbnails] LỖI: thiếu thư viện cần thiết, xem chi tiết ở trên "
                                  "(kiểm tra lại mạng/pip rồi bấm '1) Đếm & quét file đã tải' lại).",
                                  mau=MAU_LOI)
                    self._dat_trang_thai_thumb("Thiếu thư viện.", mau_diem=MAU_DIEM_TRANG_THAI_LOI)
                    mo_lai_nut_dem()
                    return

                id_kenh = thumb_core.tim_id_kenh(api_key, url_kenh)
                self._ghi_log(f"[Thumbnails]   Đã tìm thấy kênh: {id_kenh}", mau=MAU_THANH_CONG)

                self._dat_trang_thai_thumb("Đang lấy danh sách video...",
                                            mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)
                # Lấy đủ video mới nhất tới hết mốc "đến" (None = lấy hết cả kênh nếu
                # không giới hạn), rồi CẮT LẤY đúng khoảng [tu_video_thumb, den_video_thumb]
                # phía dưới - 1 = video mới nhất, khớp với cách đánh STT ở tab "Tải video".
                danh_sach_video_tho = thumb_core.lay_danh_sach_video(
                    api_key, id_kenh, so_luong_toi_da=den_video_thumb, bo_qua_shorts=bo_qua_shorts)

                if not danh_sach_video_tho:
                    self._ghi_log("[Thumbnails]   Không tìm thấy video nào.", mau=MAU_LOI)
                    self._dat_trang_thai_thumb("Không tìm thấy video.",
                                                mau_diem=MAU_DIEM_TRANG_THAI_LOI)
                    mo_lai_nut_dem()
                    return

                if tu_video_thumb > len(danh_sach_video_tho):
                    self._ghi_log(
                        f"[Thumbnails]   Kênh chỉ có {len(danh_sach_video_tho)} video (sau khi lọc) "
                        f"- không có video nào từ số {tu_video_thumb} trở đi.", mau=MAU_LOI)
                    self._dat_trang_thai_thumb("Khoảng video không hợp lệ.",
                                                mau_diem=MAU_DIEM_TRANG_THAI_LOI)
                    mo_lai_nut_dem()
                    return

                danh_sach_video = danh_sach_video_tho[tu_video_thumb - 1:]
                den_video_thuc_te = tu_video_thumb + len(danh_sach_video) - 1

                # Quét lại thư mục lưu để biết STT nào đã có sẵn file rồi - dùng
                # thumb_core.quet_stt_da_co() (dựa theo tiền tố "003_..." của tên
                # file, xem tai_1_thumbnail) để KHÔNG tải đè lại từ đầu.
                stt_da_co = thumb_core.quet_stt_da_co(thu_muc_luu)
                danh_sach_thieu = [
                    (stt, video) for stt, video in zip(
                        range(tu_video_thumb, den_video_thuc_te + 1), danh_sach_video)
                    if stt not in stt_da_co
                ]

                if tu_video_thumb > 1 or den_video_thumb:
                    self._ghi_log(
                        f"[Thumbnails]   Khoảng đã chọn      : từ video {tu_video_thumb} đến "
                        f"video {den_video_thuc_te} ({len(danh_sach_video)} video)")
                self._ghi_log(f"[Thumbnails]   Video trong khoảng  : {len(danh_sach_video)}")
                self._ghi_log(f"[Thumbnails]   Đã có (bỏ qua)      : "
                              f"{len(danh_sach_video) - len(danh_sach_thieu)}")
                self._ghi_log(f"[Thumbnails]   Còn thiếu cần tải   : {len(danh_sach_thieu)}")

                self.tong_so_video_thumb = len(danh_sach_video)
                self.danh_sach_thieu_thumb = danh_sach_thieu
                self.thu_muc_luu_thumb_da_chon = thu_muc_luu

                def cap_nhat_giao_dien():
                    self.nut_dem_thumb.configure(state="normal")
                    if danh_sach_thieu:
                        self.nut_tai_thumb.configure(state="normal")
                        self._dat_trang_thai_thumb(f"Còn {len(danh_sach_thieu)} thumbnail cần tải.",
                                                    mau_diem=MAU_DIEM_TRANG_THAI_SAN_SANG)
                        self._ghi_log("[Thumbnails] -> Bấm '2) Bắt đầu tải Thumbnails' để tiếp tục.",
                                      mau=MAU_THANH_CONG)
                    else:
                        self.nut_tai_thumb.configure(state="disabled")
                        self._dat_trang_thai_thumb("Đã tải đầy đủ.",
                                                    mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)
                        self._ghi_log("[Thumbnails] -> Đã tải đầy đủ, không còn thumbnail nào "
                                      "cần tải thêm!", mau=MAU_THANH_CONG)

                self.cua_so_goc.after(0, cap_nhat_giao_dien)

            except ValueError as loi:
                self._ghi_log(f"[Thumbnails] LỖI: {loi}", mau=MAU_LOI)
                self._dat_trang_thai_thumb("Lỗi khi tìm kênh/video.", mau_diem=MAU_DIEM_TRANG_THAI_LOI)
                mo_lai_nut_dem()
            except Exception as loi:
                self._ghi_log(f"[Thumbnails] LỖI KHÔNG MONG MUỐN: {type(loi).__name__}: {loi}",
                              mau=MAU_LOI)
                self._dat_trang_thai_thumb("Lỗi không mong muốn.", mau_diem=MAU_DIEM_TRANG_THAI_LOI)
                mo_lai_nut_dem()

        threading.Thread(target=chay_nen, daemon=True).start()

    def _bat_dau_tai_thumbnail(self):
        try:
            self._bat_dau_tai_thumbnail_that_su()
        except Exception as loi:
            # An toàn tuyệt đối: KHÔNG được để bất kỳ lỗi bất ngờ nào ở phần xử lý
            # ĐỒNG BỘ (trước khi vào luồng nền) trôi qua âm thầm - ở bản .exe đóng gói
            # (không có cửa sổ CMD) thì lỗi kiểu này vốn dĩ Tkinter sẽ nuốt mất, khiến
            # người dùng tưởng nhầm là bấm nút "không phản hồi" dù thực ra có lỗi.
            self._ghi_log(f"[Thumbnails] LỖI KHÔNG MONG MUỐN khi bấm nút: "
                          f"{type(loi).__name__}: {loi}", mau=MAU_LOI)
            messagebox.showerror("Lỗi không mong muốn", f"{type(loi).__name__}: {loi}")
            self._dang_tai_thumbnail = False
            self.nut_tai_thumb.configure(state="normal")

    def _bat_dau_tai_thumbnail_that_su(self):
        """Bước '2) Bắt đầu tải Thumbnails': tải các thumbnail còn thiếu ĐÃ ĐƯỢC
        XÁC ĐỊNH SẴN ở bước '1) Đếm & quét file đã tải' (self.danh_sach_thieu_thumb) -
        không cần dò lại kênh/API lần nữa vì thông tin video (id, tiêu đề) đã có
        sẵn từ bước đếm. Y hệt cơ chế 2 bước 'Đếm' -> 'Tải' bên tab Tải video
        (_bat_dau_dem_va_quet -> _bat_dau_tai)."""
        if self._dang_tai_thumbnail:
            return

        if not self.danh_sach_thieu_thumb:
            messagebox.showinfo(
                "Không có gì để tải",
                "Không còn thumbnail nào cần tải.\n"
                "Bấm '1) Đếm & quét file đã tải' trước."
            )
            return

        thu_muc_luu = self.thu_muc_luu_thumb_da_chon

        try:
            hue_shift = self._doc_tuy_chon_so_thuc(self.o_hue, "Tông màu (Hue)")
            saturation_shift = self._doc_tuy_chon_so_thuc(self.o_saturation, "Độ bão hoà (Saturation)")
            value_shift = self._doc_tuy_chon_so_thuc(self.o_value, "Độ sáng (Value)")
        except ValueError as loi:
            messagebox.showwarning("Sai giá trị", str(loi))
            return

        # Số luồng song song CỐ ĐỊNH ở mức an toàn (không cho người dùng chỉnh) - áp
        # dụng chung cho cả tab Video lẫn tab Thumbnails (xem SO_LUONG_CO_DINH).
        so_luong_song_song = SO_LUONG_CO_DINH

        so_can_tai = len(self.danh_sach_thieu_thumb)
        xac_nhan = messagebox.askyesno(
            "Xác nhận",
            f"Tải {so_can_tai} thumbnail còn thiếu?"
        )
        if not xac_nhan:
            return

        # Chụp lại đúng danh sách còn thiếu tại THỜI ĐIỂM bấm nút - tránh trường hợp
        # 1 luồng khác (không có ở bản này) đổi self.danh_sach_thieu_thumb giữa chừng.
        danh_sach_thieu_luc_bat_dau = list(self.danh_sach_thieu_thumb)
        danh_sach_stt = [stt for stt, _video in danh_sach_thieu_luc_bat_dau]
        danh_sach_video = [video for _stt, video in danh_sach_thieu_luc_bat_dau]

        self._huy_tai_thumbnail = False
        self._dang_tai_thumbnail = True
        self.nut_dem_thumb.configure(state="disabled")
        self.nut_tai_thumb.configure(state="disabled")
        self.nut_huy_thumb.configure(state="normal")
        self._dat_trang_thai_thumb(f"Đang tải... (0/{so_can_tai})",
                                    mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)
        self._ghi_log("\n" + "-" * 50)
        self._ghi_log(f"[Thumbnails] Bắt đầu tải {so_can_tai} thumbnail còn thiếu...")

        def chay_nen():
            try:
                def bao_tien_do(so_da_xong, tong_so, ten_video, thanh_cong, loi):
                    if thanh_cong:
                        self._ghi_log(f"[Thumbnails]   ✓ [{so_da_xong:03d}/{tong_so}] {ten_video}",
                                      mau=MAU_THANH_CONG)
                    else:
                        self._ghi_log(f"[Thumbnails]   ✗ [{so_da_xong:03d}/{tong_so}] "
                                      f"{ten_video} - {loi}", mau=MAU_LOI)
                    self._dat_trang_thai_thumb(f"Đang tải... ({so_da_xong}/{tong_so})",
                                                mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)

                so_thanh_cong, so_that_bai = thumb_core.tai_danh_sach_thumbnail(
                    danh_sach_video, thu_muc_luu, hue_shift, saturation_shift, value_shift,
                    so_luong_song_song=so_luong_song_song, ham_bao_tien_do=bao_tien_do,
                    kiem_tra_huy=lambda: self._huy_tai_thumbnail, danh_sach_stt=danh_sach_stt,
                )

                bi_huy = self._huy_tai_thumbnail
                if bi_huy:
                    self._ghi_log(f"[Thumbnails] Đã HUỶ - hoàn tất {so_thanh_cong} ảnh trước khi huỷ.",
                                  mau=MAU_LOI)
                    self._dat_trang_thai_thumb(f"Đã huỷ ({so_thanh_cong} ảnh).",
                                                mau_diem=MAU_DIEM_TRANG_THAI_LOI)
                else:
                    self._ghi_log(f"[Thumbnails] Hoàn tất: {so_thanh_cong} thành công, "
                                  f"{so_that_bai} thất bại.", mau=MAU_THANH_CONG)
                    self._dat_trang_thai_thumb(f"Đã tải xong {so_thanh_cong}/{so_can_tai} ảnh.",
                                                mau_diem=MAU_DIEM_TRANG_THAI_DANG_CHAY)
                    self._ghi_log("[Thumbnails] Nếu còn thiếu (do lỗi/mất mạng giữa chừng): bấm "
                                  "lại '1) Đếm & quét file đã tải' rồi '2) Bắt đầu tải "
                                  "Thumbnails' để tải tiếp phần còn thiếu.")

                    def hien_thong_bao():
                        messagebox.showinfo(
                            "Đã tải xong",
                            f"Đã tải xong {so_thanh_cong} thumbnail "
                            + (f"({so_that_bai} lỗi) " if so_that_bai else "")
                            + f"vào thư mục:\n{thu_muc_luu}",
                        )
                    self.cua_so_goc.after(0, hien_thong_bao)

            except Exception as loi:
                self._ghi_log(f"[Thumbnails] LỖI KHÔNG MONG MUỐN: {type(loi).__name__}: {loi}",
                              mau=MAU_LOI)
                self._dat_trang_thai_thumb("Lỗi không mong muốn.", mau_diem=MAU_DIEM_TRANG_THAI_LOI)
            finally:
                self._dang_tai_thumbnail = False
                # Bắt buộc phải bấm lại '1) Đếm & quét file đã tải' trước khi tải
                # tiếp - giống hệt tab Video (nut_dem bật lại, nut_tai tắt đi) - để
                # luôn quét lại thư mục trước khi tải, tránh tải trùng/đè.
                self.cua_so_goc.after(0, lambda: self.nut_dem_thumb.configure(state="normal"))
                self.cua_so_goc.after(0, lambda: self.nut_tai_thumb.configure(state="disabled"))
                self.cua_so_goc.after(0, lambda: self.nut_huy_thumb.configure(state="disabled"))

        threading.Thread(target=chay_nen, daemon=True).start()

    def _huy_tai_thumb(self):
        self._huy_tai_thumbnail = True
        self.nut_huy_thumb.configure(state="disabled")
        self._ghi_log("[Thumbnails] Đang huỷ (chờ các ảnh đang tải dở xong nốt)...", mau=MAU_LOI)

    def _dat_trang_thai_thumb(self, chu, mau_diem=None):
        def cap_nhat():
            self.nhan_trang_thai_thumb.configure(text=chu)
            if mau_diem:
                self.diem_trang_thai_thumb.configure(fg=mau_diem)
        self.cua_so_goc.after(0, cap_nhat)


def main():
    cua_so_goc = tk.Tk()
    UngDungTaiVideo(cua_so_goc)
    cua_so_goc.mainloop()


if __name__ == "__main__":
    # Ẩn cửa sổ CMD đen (nếu an toàn để ẩn - xem giải thích trong hàm) trước khi
    # dựng giao diện, để không bị "nháy đen" 1 khung console trước khi cửa sổ chính hiện ra.
    an_cua_so_cmd_neu_an_toan()

    try:
        main()
    except Exception as loi:
        # QUAN TRỌNG: vì cửa sổ CMD có thể đã bị ẩn ở trên, print() sẽ KHÔNG hiển thị
        # được ở đâu cả nếu chương trình lỗi ngay lúc khởi động - phải dùng messagebox
        # (hộp thoại cửa sổ) để chắc chắn người dùng luôn nhìn thấy lỗi, thay vì
        # chương trình "biến mất" không dấu vết.
        try:
            import tkinter as _tk
            from tkinter import messagebox as _messagebox
            _cua_so_loi = _tk.Tk()
            _cua_so_loi.withdraw()
            _messagebox.showerror(
                "Chương trình gặp lỗi khi khởi động",
                f"{type(loi).__name__}: {loi}\n\n"
                "Hãy chụp lại thông báo này và gửi cho người hỗ trợ.",
            )
            _cua_so_loi.destroy()
        except Exception:
            # Nếu ngay cả tkinter cũng không dựng nổi (lỗi rất hiếm), đành in ra
            # console như phương án cuối cùng - phòng khi console vẫn còn hiển thị.
            print(f"CHƯƠNG TRÌNH GẶP LỖI: {type(loi).__name__}: {loi}")


# =====================================================================
# HƯỚNG DẪN ĐÓNG GÓI THÀNH FILE .EXE (không hiện cửa sổ CMD đen,
# icon riêng cho file .exe)
# =====================================================================
#
# CÁCH NHANH NHẤT: double-click vào file "dong_goi.bat" nằm cùng thư mục với
# file này. Nó sẽ TỰ mở CMD, TỰ cài các thư viện cần thiết (pyinstaller,
# psutil, yt-dlp) và TỰ chạy lệnh đóng gói bên dưới - không cần gõ
# tay từng lệnh. File .exe hoàn chỉnh sẽ nằm trong thư mục "dist" sau khi
# chạy xong. (Máy chạy file .bat này vẫn phải có sẵn Python - xem Bước 1
# bên dưới nếu chưa có, vì bản thân Python thì không tự cài được.)
#
# CÁCH LÀM TAY (nếu muốn tự kiểm soát từng bước):
#
# Nguyên nhân hiện cửa sổ CMD đen phía sau: khi đóng gói bằng PyInstaller mà
# KHÔNG thêm cờ --windowed (hoặc --noconsole), Windows sẽ luôn mở kèm 1 cửa sổ
# console cho chương trình, kể cả khi chương trình là giao diện cửa sổ (GUI).
# Đoạn code "ẨN CỬA SỔ CMD ĐEN" ở đầu file đã tự ẩn nó đi khi ứng dụng chạy,
# nhưng để triệt để và gọn nhất, hãy đóng gói lại bằng đúng lệnh dưới đây:
#
#   1. Cài công cụ đóng gói (nếu chưa có):
#        pip install pyinstaller psutil
#      (psutil dùng cho tính năng Tạm dừng/Tiếp tục khi tải)
#      Lưu ý: bản thân chương trình đã TỰ CÀI psutil/yt-dlp còn thiếu khi
#      chạy trực tiếp bằng "python", nhưng khi ĐÓNG GÓI thành .exe thì các thư viện
#      này phải có sẵn LÚC ĐÓNG GÓI (không tự cài được sau khi đã đóng gói xong),
#      nên vẫn cần cài trước bằng lệnh trên rồi mới chạy pyinstaller.
#
#   2. Đứng ở thư mục chứa tai_video_gui.py, tai_video_core.py và
#      thư mục con "assets" (chứa icon.ico, icon.png, banner.png), rồi chạy:
#
#        pyinstaller --onefile --windowed --icon=assets\icon.ico ^
#          --add-data "assets;assets" --name VideoDownloader tai_video_gui.py
#
#      Giải thích các cờ:
#        --onefile     -> gộp thành 1 file .exe duy nhất
#        --windowed    -> KHÔNG mở cửa sổ CMD đen (đây là cờ quan trọng nhất
#                         để khắc phục vấn đề bạn gặp)
#        --icon=...    -> đặt LOGO cho chính file .exe (icon hiện trong File
#                         Explorer / trên màn hình Desktop)
#        --add-data    -> đóng gói kèm ảnh banner + icon vào trong file .exe
#
#   3. File .exe hoàn chỉnh sẽ nằm trong thư mục "dist" vừa được tạo ra:
#        dist\VideoDownloader.exe
#
#   Muốn đổi sang icon/ảnh nền khác của riêng bạn: chỉ cần thay file
#   assets\icon.ico (hoặc assets\banner.png) bằng ảnh của bạn, giữ nguyên tên
#   file, rồi đóng gói lại theo đúng lệnh ở bước 2.
# =====================================================================
