import io

from PIL import Image

from app.creative.render import SIZES, TEMPLATES, CreativeData, render_png, render_reel_mp4

D = CreativeData(title="Noise-Cancelling Kopfhörer Over-Ear mit sehr langem Produktnamen für den Umbruchtest",
                 price_cents=1999, reference_price_cents=9999, discount_pct=80.0, label="Preisfehler-Verdacht",
                 category="technik", price_stand="25.11.2026, 12:00 Uhr", coupon_code="SAVE10")


def test_all_templates_all_sizes():
    for tpl in TEMPLATES:
        for kind in ("post", "story", "pin"):
            img = Image.open(io.BytesIO(render_png(D, kind, tpl)))
            assert img.size == SIZES[kind]


def test_reel_video():
    mp4 = render_reel_mp4(D, seconds_per_frame=1.0)
    assert mp4[4:8] == b"ftyp" and len(mp4) > 10_000
