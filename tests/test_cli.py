"""Tests for the CLI interface."""

from unittest.mock import MagicMock, patch

from ledbadgeprogrammer.cli import build_badge_from_args, main


def test_build_badge_from_args():
    args = [
        "--width",
        "48",
        "--height",
        "12",
        "-p",
        "/dev/test_port",
        "speed=5",
        "effect=left",
        "blink=on",
        "marquee=on",
        "invert=on",
        "test_12x48.png",
        "speed=2",
        "blink=off",
        "marquee=off",
        "invert=off",
        "Hello",
    ]
    badge = build_badge_from_args(args)
    assert len(badge.messages) == 2

    msg1 = badge.messages[0]
    assert msg1.speed == 5
    assert msg1.effect == 0  # left
    assert msg1.blink is True
    assert msg1.marquee is True

    msg2 = badge.messages[1]
    assert msg2.speed == 2
    assert msg2.blink is False
    assert msg2.marquee is False


def test_main_cli_execution():
    with patch("serial.Serial") as mock_serial:
        mock_instance = MagicMock()
        mock_serial.return_value = mock_instance
        exit_code = main(["-p", "/dev/mock_serial", "test_12x48.png"])
        assert exit_code == 0
        mock_serial.assert_called_once_with("/dev/mock_serial", 4800)


def test_main_cli_dry_run(capsys):
    exit_code = main(["--dry-run", "test_12x48.png", "Hello"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Dry run successful!" in captured.out
    assert "Messages: 2" in captured.out


def test_main_cli_list_ports(capsys):
    with patch(
        "ledbadgeprogrammer.cli.list_serial_ports",
        return_value=["/dev/cu.usbserial-10"],
    ):
        exit_code = main(["--list-ports"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "/dev/cu.usbserial-10" in captured.out
