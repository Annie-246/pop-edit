"""Bảng màu. Màu viết dạng RGB. Có thể đặt "theme" trong project.json là tên có sẵn hoặc 1 dict ghi đè từng màu."""

BASE = dict(
    bg_light=(247, 237, 224),     # nền sáng (be)
    grid_light=(238, 226, 210),
    dot_light=(222, 150, 172),
    bg_dark=(241, 188, 198),      # nền "đậm" (hồng phấn)
    grid_dark=(246, 206, 214),
    dot_dark=(255, 246, 236),
    accent=(184, 62, 98),         # màu nhấn (tay cầm ô chọn chữ, nhãn)
    deep=(154, 44, 80),           # số lớn trên nền đậm
    ink=(34, 22, 30),             # chữ tiêu đề
    sel=(244, 177, 200),          # ô chọn chữ trên nền sáng
    sel_dark=(255, 250, 244),     # ô chọn chữ trên nền đậm
    wipe=(224, 126, 154),         # tấm chuyển cảnh
    spike=(216, 111, 140),        # đường chia + viền swipe
    cream=(255, 246, 236),
    lead_light=(150, 138, 148),   # chữ dẫn (nghiêng, xám) trên nền sáng
    lead_dark=(140, 100, 112),
    small_light=(160, 146, 152),
    shadow=(60, 30, 45),
    plate=(255, 252, 247),        # nền thẻ / sticker
    sub_stroke=(40, 20, 28),      # viền chữ phụ đề
)

THEMES = {
    "be-hong": BASE,
    "xanh": dict(BASE,
                 bg_light=(247, 249, 252), grid_light=(226, 232, 242), dot_light=(120, 150, 230),
                 bg_dark=(26, 86, 240), grid_dark=(60, 108, 242), dot_dark=(255, 255, 255),
                 accent=(26, 86, 240), deep=(255, 255, 255), ink=(15, 18, 30), sel=(190, 208, 255),
                 sel_dark=(255, 255, 255), wipe=(26, 86, 240), spike=(26, 86, 240), cream=(255, 255, 255),
                 lead_light=(130, 138, 160), lead_dark=(225, 235, 255), small_light=(150, 158, 178),
                 shadow=(20, 30, 70), sub_stroke=(10, 18, 50)),
    "tim-pastel": dict(BASE,
                       bg_light=(246, 242, 250), grid_light=(232, 224, 244), dot_light=(168, 140, 220),
                       bg_dark=(214, 196, 240), grid_dark=(226, 212, 246), dot_dark=(255, 255, 255),
                       accent=(110, 60, 190), deep=(80, 36, 150), ink=(28, 20, 44), sel=(214, 196, 250),
                       sel_dark=(255, 255, 255), wipe=(150, 110, 220), spike=(150, 110, 220), cream=(255, 255, 255),
                       lead_light=(146, 136, 164), lead_dark=(100, 76, 140), small_light=(160, 150, 176),
                       shadow=(50, 30, 80), sub_stroke=(30, 16, 56)),
}


def resolve(spec):
    """spec: None | tên theme | dict ghi đè."""
    if spec is None:
        return dict(THEMES["be-hong"])
    if isinstance(spec, str):
        if spec not in THEMES:
            raise SystemExit(f"Theme '{spec}' không có. Có sẵn: {', '.join(THEMES)}")
        return dict(THEMES[spec])
    base = dict(THEMES[spec.get("base", "be-hong")])
    for k, v in spec.items():
        if k != "base":
            base[k] = tuple(v)
    return base
