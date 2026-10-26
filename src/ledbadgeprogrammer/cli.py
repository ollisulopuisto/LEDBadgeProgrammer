"""Command-line interface for LED Badge Programmer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ledbadgeprogrammer.badge import EFFECTS, BadgeConfig, LEDBadge, Message


def list_serial_ports() -> list[str]:
    """Return a list of available serial port device names."""
    try:
        from serial.tools import list_ports

        return [port.device for port in list_ports.comports()]
    except (ImportError, OSError):
        return []


def default_port() -> str:
    """Select a sensible default port for the current operating system."""
    ports = list_serial_ports()
    # On macOS, prioritize USB serial devices
    usb_ports = [
        p for p in ports if "usbserial" in p.lower() or "wchusbserial" in p.lower()
    ]
    if usb_ports:
        return usb_ports[0]
    if ports:
        return ports[0]
    if sys.platform == "darwin":
        return "/dev/cu.usbserial"
    if sys.platform == "win32":
        return "COM1"
    return "/dev/ttyUSB0"


def build_badge_from_args(args_list: list[str]) -> LEDBadge:
    """Parse command line arguments and assemble an LEDBadge instance."""
    parser = argparse.ArgumentParser(
        prog="ledbadge",
        description="Program B1248W and compatible scrolling LED name badges.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=48,
        help="Width of badge display in pixels (default: 48)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=12,
        help="Height of badge display in pixels (default: 12)",
    )
    parser.add_argument(
        "-p",
        "--port",
        default=None,
        help="Serial port (default: auto-detected or /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Assemble messages and validate headers without writing to serial port.",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List available serial ports and exit.",
    )
    parser.add_argument(
        "coms",
        nargs="*",
        help="Options (<key>=<value>) and message strings or image filepaths.",
    )

    parsed = parser.parse_args(args_list)

    if parsed.list_ports:
        ports = list_serial_ports()
        if ports:
            print("Available serial ports:")
            for p in ports:
                print(f"  {p}")
        else:
            print("No serial ports detected.")
        sys.exit(0)

    if not parsed.coms:
        parser.print_help()
        sys.exit(1)

    port = parsed.port or default_port()
    config = BadgeConfig(width=parsed.width, height=parsed.height, port=port)
    badge = LEDBadge(config)

    speed = 1
    effect = "fix"
    blink = False
    marquee = False
    invert = False
    font: str | None = None
    halign = "left"
    valign = "middle-down"
    wrap = "none"

    for c in parsed.coms:
        if c.startswith("speed="):
            speed = int(c[6:])
        elif c.startswith("effect="):
            effect = c[7:].lower()
        elif c.startswith("blink="):
            blink = c.endswith("on")
        elif c.startswith("marquee="):
            marquee = c.endswith("on")
        elif c.startswith("invert="):
            invert = c.endswith("on")
        elif c.startswith("font="):
            font = c[5:]
        elif c.startswith("halign="):
            halign = c[7:]
        elif c.startswith("valign="):
            valign = c[7:]
        elif c.startswith("wrap="):
            wrap = c[5:]
        else:
            if effect not in EFFECTS:
                raise ValueError(
                    f"Unknown effect '{effect}'. Available effects: {', '.join(EFFECTS.keys())}"
                )

            m = Message(config)
            m.effect = EFFECTS[effect]
            m.speed = speed
            m.blink = blink
            m.marquee = marquee

            if Path(c).is_file():
                m.set_image(c, halign=halign, valign=valign, invert=invert)
            else:
                m.set_text(
                    c,
                    font_path=font,
                    halign=halign,
                    valign=valign,
                    wrap=wrap,
                    invert=invert,
                )

            badge.add_message(m)

    return badge


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    args_list = argv if argv is not None else sys.argv[1:]

    # Handle quick help or --list-ports before requiring arguments
    if "--list-ports" in args_list:
        ports = list_serial_ports()
        if ports:
            print("Available serial ports:")
            for p in ports:
                print(f"  {p}")
        else:
            print("No serial ports detected.")
        return 0

    if not args_list or "-h" in args_list or "--help" in args_list:
        build_badge_from_args(["--help"])
        return 0

    try:
        badge = build_badge_from_args(args_list)
        if "--dry-run" in args_list:
            conf, img, data = badge.build_payload()
            print(f"Dry run successful! Messages: {len(badge.messages)}")
            print(f"Config header bytes: {len(conf)}")
            print(f"Image header bytes: {len(img)}")
            print(
                f"Image rows: {len(data)}, row width: {len(data[0]) if data else 0} bytes"
            )
            return 0

        print(f"Sending to LED Badge on {badge.config.port}...")
        badge.send()
        print("Done!")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
