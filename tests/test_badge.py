"""Tests for LEDBadge protocol framing and serial sending."""

from unittest.mock import MagicMock

import pytest

from ledbadgeprogrammer.badge import EFFECTS, BadgeConfig, LEDBadge, Message


def test_badge_max_messages():
    config = BadgeConfig(width=48, height=12)
    badge = LEDBadge(config)
    for _ in range(8):
        badge.add_message(Message(config))
    with pytest.raises(ValueError, match="Maximum 8 messages"):
        badge.add_message(Message(config))


def test_badge_build_payload_empty():
    badge = LEDBadge()
    conf, img, data = badge.build_payload()
    assert conf == b""
    assert img == b""
    assert data == []


def test_badge_build_payload_single_message():
    config = BadgeConfig(width=48, height=12)
    badge = LEDBadge(config)
    msg = Message(config)
    msg.effect = EFFECTS["left"]
    msg.speed = 3
    msg.blink = True
    msg.marquee = False
    msg.set_image("test_12x48.png")
    badge.add_message(msg)

    confheader, imgheader, image = badge.build_payload()

    # confheader starts with 0x00, followed by 8 config bytes (total 9 bytes)
    assert len(confheader) == 9
    assert confheader[0] == 0x00
    # effect 0 (left) + speed 3 * 16 (48 = 0x30) + blink 0x08 = 0x38
    assert confheader[1] == 0x38

    # imgheader: 8 messages * 4 bytes + 1 byte stop (0x00) = 33 bytes
    assert len(imgheader) == 33
    assert imgheader[-1] == 0x00

    # 12 lines of image data
    assert len(image) == 12
    for line in image:
        assert len(line) == 6


def test_badge_build_payload_multiple_messages():
    config = BadgeConfig(width=48, height=12)
    badge = LEDBadge(config)

    msg1 = Message(config)
    msg1.set_image("test_12x48.png")  # width 6 bytes
    badge.add_message(msg1)

    msg2 = Message(config)
    msg2.set_image("test_12x48.png")  # width 6 bytes
    badge.add_message(msg2)

    confheader, imgheader, image = badge.build_payload()

    assert len(confheader) == 9
    assert len(image) == 12
    # Combined width is 6 + 6 = 12 bytes
    for line in image:
        assert len(line) == 12

    # In imgheader:
    # First entry (msg 0): lastw=0, 0x08, iw=0, 0x00 -> bytes([0, 8, 0, 0])
    # Second entry (msg 1): lastw=6, 0x08, iw=6, 0x00 -> bytes([6, 8, 6, 0])
    assert imgheader[0:4] == b"\x00\x08\x00\x00"
    assert imgheader[4:8] == b"\x06\x08\x06\x00"


def test_badge_send_mock_serial():
    config = BadgeConfig(width=48, height=12, port="/dev/mock_tty")
    badge = LEDBadge(config)
    msg = Message(config)
    msg.set_image("test_12x48.png")
    badge.add_message(msg)

    mock_serial_cls = MagicMock()
    mock_instance = MagicMock()
    mock_serial_cls.Serial.return_value = mock_instance

    badge.send(serial_module=mock_serial_cls)

    mock_serial_cls.Serial.assert_called_once_with("/dev/mock_tty", 4800)
    # Check that b"Hello" and headers and image rows were written
    written_data = [call.args[0] for call in mock_instance.write.call_args_list]
    assert written_data[0] == b"Hello"
    confheader, imgheader, _ = badge.build_payload()
    assert written_data[1] == confheader + imgheader
    mock_instance.close.assert_called_once()
