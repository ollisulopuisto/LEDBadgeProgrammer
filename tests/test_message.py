"""Tests for ledbadgeprogrammer Message class."""

from PIL import Image

from ledbadgeprogrammer.badge import (
    EFFECTS,
    BadgeConfig,
    Message,
    get_text_size,
    load_font,
    resolve_font_path,
)


def test_message_defaults():
    config = BadgeConfig(width=48, height=12)
    msg = Message(config)
    assert msg.effect == EFFECTS["fix"]
    assert msg.speed == 1
    assert not msg.blink
    assert not msg.marquee
    assert msg.width_bytes == 0
    assert len(msg.image_rows) == 12


def test_message_set_image_from_file():
    config = BadgeConfig(width=48, height=12)
    msg = Message(config)
    msg.set_image("test_12x48.png")
    assert msg.width_bytes == 6  # 48 pixels / 8 = 6 bytes
    assert len(msg.image_rows) == 12
    for row in msg.image_rows:
        assert len(row) == 6


def test_message_set_image_with_invert():
    config = BadgeConfig(width=48, height=12)
    msg_normal = Message(config)
    msg_normal.set_image("test_12x48.png", invert=False)

    msg_inverted = Message(config)
    msg_inverted.set_image("test_12x48.png", invert=True)

    assert msg_normal.width_bytes == msg_inverted.width_bytes
    # Every byte in inverted should be bitwise NOT of normal
    for r_norm, r_inv in zip(msg_normal.image_rows, msg_inverted.image_rows):
        for b_norm, b_inv in zip(r_norm, r_inv):
            assert b_norm ^ b_inv == 0xFF


def test_message_set_text():
    config = BadgeConfig(width=48, height=12)
    msg = Message(config)
    msg.set_text("TEST", font_path="pilfonts/helvR08.pil")
    assert msg.width_bytes > 0
    assert len(msg.image_rows) == 12


def test_message_text_word_wrap():
    config = BadgeConfig(width=48, height=12)
    msg = Message(config)
    msg.set_text(
        "This is a longer text that must wrap across multiple screens",
        font_path="pilfonts/helvR08.pil",
        wrap="word",
    )
    assert msg.width_bytes > 6  # Exceeds single screen width of 6 bytes (48px)


def test_message_text_char_wrap():
    config = BadgeConfig(width=48, height=12)
    msg = Message(config)
    msg.set_text(
        "Supercalifragilisticexpialidocious",
        font_path="pilfonts/helvR08.pil",
        wrap="char",
    )
    assert msg.width_bytes > 6


def test_message_crop_blank_image():
    config = BadgeConfig(width=48, height=12)
    msg = Message(config)
    blank = Image.new("L", (20, 12), "black")
    cropped = msg.crop_empty(blank)
    assert cropped.size[0] == 1
    assert cropped.size[1] == 12


def test_message_set_image_non_byte_aligned_and_padding():
    # Width 44 is not a multiple of 8 (5 bytes + 4 bits); Height 11 < badge height 12
    config = BadgeConfig(width=44, height=12)
    msg_normal = Message(config)
    msg_normal.set_image("test_11x44.png", invert=False)
    assert msg_normal.width_bytes == 6  # ceil(44 / 8) = 6
    assert len(msg_normal.image_rows) == 12
    for row in msg_normal.image_rows:
        assert len(row) == 6

    msg_inverted = Message(config)
    msg_inverted.set_image("test_11x44.png", invert=True)
    assert msg_inverted.width_bytes == 6
    assert len(msg_inverted.image_rows) == 12

    # Verify that the active 44 bits are inverted and the unused 4 bits in byte 6 are 0
    rem_mask = 0xF0  # 4 bits active in the 6th byte
    for r_norm, r_inv in zip(msg_normal.image_rows[:11], msg_inverted.image_rows[:11]):
        for b_norm, b_inv in zip(r_norm[:5], r_inv[:5]):
            assert b_norm ^ b_inv == 0xFF
        assert (r_norm[5] ^ r_inv[5]) == rem_mask
        assert (r_inv[5] & ~rem_mask) == 0


def test_resolve_font_path():
    p = resolve_font_path("helvR08.pil")
    assert p.is_file()
    assert p.name == "helvR08.pil"


def test_load_font_caching():
    p = resolve_font_path("helvR08.pil")
    font1 = load_font(p)
    font2 = load_font(p)
    assert font1 is font2


def test_message_invert_various_widths():
    # Test various width alignments: byte-aligned (8, 48) and unaligned (7, 44, 45)
    for width in [7, 8, 44, 45, 48]:
        config = BadgeConfig(width=width, height=12)
        im = Image.new("1", (width, 12), 0)
        for x in range(width):
            im.putpixel((x, x % 12), 1)

        msg_norm = Message(config)
        msg_norm.set_image(im, invert=False)

        msg_inv = Message(config)
        msg_inv.set_image(im, invert=True)

        assert msg_norm.width_bytes == msg_inv.width_bytes
        rem = width % 8
        last_mask = ((0xFF << (8 - rem)) & 0xFF) if rem != 0 else 0xFF

        for r_norm, r_inv in zip(msg_norm.image_rows, msg_inv.image_rows):
            if len(r_norm) > 1:
                for b_norm, b_inv in zip(r_norm[:-1], r_inv[:-1]):
                    assert b_norm ^ b_inv == 0xFF
            assert (r_norm[-1] ^ r_inv[-1]) == last_mask
            assert (r_inv[-1] & ~last_mask) == 0


def test_resolve_font_path_caching():
    resolve_font_path.cache_clear()
    p1 = resolve_font_path("helvR08.pil")
    p2 = resolve_font_path("helvR08.pil")
    assert p1 == p2
    info = resolve_font_path.cache_info()
    assert info.hits == 1

    p_default1 = resolve_font_path()
    p_default2 = resolve_font_path()
    assert p_default1 == p_default2
    info2 = resolve_font_path.cache_info()
    assert info2.hits == 2


def test_get_text_size_caching():
    get_text_size.cache_clear()
    p = resolve_font_path("helvR08.pil")
    font = load_font(p)

    # Empty string handling
    assert get_text_size(font, "") == (0, 0)

    # First call - cache miss
    size1 = get_text_size(font, "Hello World")
    assert size1[0] > 0
    assert size1[1] > 0
    info1 = get_text_size.cache_info()
    assert info1.misses >= 1

    # Second call with identical arguments - cache hit
    size2 = get_text_size(font, "Hello World")
    assert size1 == size2
    info2 = get_text_size.cache_info()
    assert info2.hits >= 1
