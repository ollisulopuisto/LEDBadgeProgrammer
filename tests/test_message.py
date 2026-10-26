"""Tests for ledbadgeprogrammer Message class."""

from PIL import Image

from ledbadgeprogrammer.badge import EFFECTS, BadgeConfig, Message, resolve_font_path


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


def test_resolve_font_path():
    p = resolve_font_path("helvR08.pil")
    assert p.is_file()
    assert p.name == "helvR08.pil"
