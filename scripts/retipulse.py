#!/usr/bin/env python3
"""
retipulse.py - RetiPulse: live LoRa status and settings for a NomadNet page.

Every time the page loads, this reads the Reticulum config for enabled
RNodeInterface radios and runs rnstatus for their live status (Up/Down,
rate, noise floor, airtime, traffic). Change a setting and the page shows it
on the next load; no cron job or cache needed. If no RNodeInterface is
enabled, the page shows "LoRa Offline".

Only settings on the SAFE_KEYS list are ever shown. Anything else in the
config, such as IFAC passphrases or network names, is never printed.

Run directly:   ./retipulse.py        (prints the Micron block)
Or import:      from retipulse import get_lora_micron
"""

import os

# ============================ CONFIGURATION ============================

# Leave as None to find the config the same way Reticulum does:
# /etc/reticulum, then ~/.config/reticulum, then ~/.reticulum.
CONFIG_PATH = None

# Interface types treated as LoRa radios. Only enabled ones are shown
# (enabled = yes, or interface_enabled = true, in the config).
LORA_TYPES = ("RNodeInterface",)

SHOW_CONFIG_BLOCK = True  # also show the settings in config-file format

# rnstatus provides the live status. Leave as None to look in your PATH and
# ~/.local/bin; set a full path if it lives somewhere else.
RNSTATUS_PATH = None
RNSTATUS_TIMEOUT = 10     # seconds

# Live status lines shown from rnstatus, and the label used for each.
# Anything else rnstatus prints for the interface is left out.
LIVE_KEYS = {
    "Status": "Status",
    "Mode": "Mode",
    "Rate": "Rate",
    "Noise Fl.": "Noise floor",
    "Intrfrnc.": "Interference",
    "Battery": "Battery",
    "Airtime": "Airtime",
    "Ch. Load": "Channel load",
    "Traffic": "Traffic",
}

# The only settings ever shown, in display order. Anything not listed here
# (passphrases, network names, ports, identities...) is never printed.
SAFE_KEYS = (
    "frequency", "bandwidth", "spreadingfactor", "codingrate", "txpower",
    "mode", "airtime_limit_long", "airtime_limit_short",
    "announce_interval", "discovery_name", "discovery_stamp_value",
    "discovery_encrypt", "publish_ifac",
)

# =======================================================================

import re
import shutil
import subprocess
from datetime import datetime

TRUE_WORDS = ("yes", "true", "on", "1")


def find_config():
    if CONFIG_PATH:
        return os.path.expanduser(CONFIG_PATH)
    for path in ("/etc/reticulum/config",
                 os.path.expanduser("~/.config/reticulum/config"),
                 os.path.expanduser("~/.reticulum/config")):
        if os.path.isfile(path):
            return path
    return os.path.expanduser("~/.reticulum/config")


def strip_comment(line):
    """Remove a # comment, unless the # is inside quotes."""
    out, quote = [], None
    for ch in line:
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            break
        out.append(ch)
    return "".join(out).strip()


def parse_config(text):
    """Parse the Reticulum (ConfigObj-style) config into interface dicts.

    Returns a list of {"name", "settings", "subinterfaces": [...]} for every
    interface under [interfaces]. [[Name]] is an interface; [[[Name]]] is a
    sub-interface, as used by RNodeMultiInterface.
    """
    interfaces = []
    section = None        # top-level section name, e.g. "interfaces"
    current = None        # dict we're filling
    iface = None          # current [[interface]]
    for raw in text.splitlines():
        line = strip_comment(raw)
        if not line:
            continue
        m = re.fullmatch(r"(\[+)\s*(.*?)\s*(\]+)", line)
        if m:
            depth, name = len(m.group(1)), m.group(2)
            if depth == 1:
                section, current, iface = name.lower(), None, None
            elif section == "interfaces" and depth == 2:
                iface = {"name": name, "settings": {}, "subinterfaces": []}
                interfaces.append(iface)
                current = iface["settings"]
            elif section == "interfaces" and depth == 3 and iface is not None:
                sub = {"name": name, "settings": {}}
                iface["subinterfaces"].append(sub)
                current = sub["settings"]
            else:
                current = None
            continue
        if current is not None and "=" in line:
            key, value = line.split("=", 1)
            current[key.strip().lower()] = value.strip().strip("\"'")
    return interfaces


# ----------------------------- rnstatus --------------------------------

def find_rnstatus():
    if RNSTATUS_PATH:
        return os.path.expanduser(RNSTATUS_PATH)
    return shutil.which("rnstatus") or os.path.expanduser("~/.local/bin/rnstatus")


def run_rnstatus():
    """Return (output, error). error is None when rnstatus ran."""
    try:
        result = subprocess.run([find_rnstatus()], capture_output=True, text=True,
                                timeout=RNSTATUS_TIMEOUT)
        return result.stdout, None
    except FileNotFoundError:
        return "", "rnstatus not found"
    except subprocess.TimeoutExpired:
        return "", "rnstatus timed out"
    except Exception as e:
        return "", type(e).__name__


def parse_rnstatus(text):
    """{'My-RNode': {'type': 'RNodeInterface', 'Status': 'Up', ...}}

    Each interface starts with a 'Type[Name]' line, followed by 'Key : Value'
    lines. A line with no colon (like the second Traffic line) continues the
    previous value.
    """
    found, current, last_key = {}, None, None
    for line in text.splitlines():
        m = re.fullmatch(r"\s*(\w+)\[(.+)\]\s*", line)
        if m:
            current = {"type": m.group(1)}
            found[m.group(2)] = current
            last_key = None
            continue
        if current is None or not line.strip():
            if not line.strip():
                last_key = None
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            last_key = key.strip()
            current[last_key] = value.strip()
        elif last_key:
            current[last_key] += "\n" + line.strip()
    return found


# ----------------------------- formatting ------------------------------

def esc(text):
    return str(text).replace("`", "\\`")


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_enabled(settings):
    """Reticulum treats an interface as off unless it's explicitly enabled."""
    for key in ("interface_enabled", "enabled"):
        if key in settings:
            return settings[key].lower() in TRUE_WORDS
    return False


def fmt_freq(v):
    f = num(v)
    return f"{f / 1e6:.3f} MHz" if f else v


def fmt_bw(v):
    b = num(v)
    if not b:
        return v
    return f"{b / 1e3:g} kHz"


def bitrate(settings):
    """Approximate on-air bitrate, using the same formula as Reticulum."""
    sf, bw, cr = (num(settings.get(k)) for k in ("spreadingfactor", "bandwidth", "codingrate"))
    if not (sf and bw and cr):
        return None
    bps = sf * ((4.0 / cr) / (2 ** sf / (bw / 1000))) * 1000
    return f"{bps / 1000:.2f} kbps" if bps >= 1000 else f"{bps:.0f} bps"


def summary_rows(settings):
    rows = []
    if "frequency" in settings:
        rows.append(("Frequency", fmt_freq(settings["frequency"])))
    if "bandwidth" in settings:
        rows.append(("Bandwidth", fmt_bw(settings["bandwidth"])))
    if "spreadingfactor" in settings:
        rows.append(("Spreading factor", f"SF{settings['spreadingfactor']}"))
    if "codingrate" in settings:
        rows.append(("Coding rate", f"4/{settings['codingrate']}"))
    if "txpower" in settings:
        rows.append(("TX power", f"{settings['txpower']} dBm"))
    rate = bitrate(settings)
    if rate:
        rows.append(("Est. bitrate", rate))
    if "mode" in settings:
        rows.append(("Mode", settings["mode"]))
    return rows


def config_block(name, settings, depth=2):
    lines = ["[" * depth + name + "]" * depth]
    for key in SAFE_KEYS:
        if key in settings:
            lines.append(f"  {key} = {settings[key]}")
    return lines


def live_rows(live):
    rows = []
    for key, label in LIVE_KEYS.items():
        if key in ("Status", "Mode") or key not in live:
            continue
        value = live[key]
        if value.lower() == "unknown":
            continue
        parts = [" ".join(p.split()) for p in value.split("\n")]
        rows.append((label, parts[0]))
        rows += [("", p) for p in parts[1:]]
    return rows


def status_word(live):
    status = (live or {}).get("Status", "")
    if not status:
        return "`Ff00Not running`f"
    color = "`F0f0" if status.lower() == "up" else "`Ff00"
    return f"{color}{esc(status)}`f"


def build_micron(interfaces, path, status_text="", status_error=None):
    out = []
    radios = [i for i in interfaces
              if i["settings"].get("type") in LORA_TYPES and is_enabled(i["settings"])]
    live_all = parse_rnstatus(status_text)
    up = [i for i in radios
          if live_all.get(i["name"], {}).get("Status", "").lower() == "up"]

    # Overall banner
    if not radios:
        out.append("`c`Ff00`!LoRa Offline`!`f`a")
        out.append("`cNo LoRa interfaces are enabled on this node.`a")
        return "\n".join(out) + "\n"
    if status_error:
        out.append("`c`Fff0`!LoRa status unknown`!`f`a")
        out.append(f"`cCouldn't get live status ({esc(status_error)}); showing configured settings.`a")
    elif up:
        out.append("`c`F0f0`!LoRa Online`!`f`a")
    else:
        out.append("`c`Ff00`!LoRa Offline`!`f`a")
        out.append("`cLoRa is enabled in the config, but no radio is up right now.`a")

    try:
        changed = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%I:%M%p %m/%d/%Y").lstrip("0")
        out.append(f"`c`F888Settings from the Reticulum config, last changed {changed}`f`a")
    except OSError:
        pass
    out.append("")

    for iface in radios:
        s = iface["settings"]
        live = live_all.get(iface["name"])
        out.append(f">>{esc(iface['name'])}")
        mode = (live or {}).get("Mode") or s.get("mode")
        line = "Status".ljust(18) + (status_word(live) if not status_error else "Unknown")
        if mode:
            line += f"  ({esc(mode)})"
        out.append(line)
        for label, value in (live_rows(live) if live else []):
            out.append(label.ljust(18) + esc(value))
        out.append("")

        out.append("`!Configured settings`!")
        for label, value in summary_rows(s):
            if label != "Mode":
                out.append(label.ljust(18) + esc(value))
        if SHOW_CONFIG_BLOCK:
            out.append("")
            out.append("`=")
            out += config_block(iface["name"], s)
            out.append("`=")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def get_lora_micron():
    path = find_config()
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return f"Can't read the Reticulum config at {esc(path)} ({type(e).__name__})."
    try:
        interfaces = parse_config(text)
        enabled = any(i["settings"].get("type") in LORA_TYPES and is_enabled(i["settings"])
                      for i in interfaces)
        status_text, status_error = run_rnstatus() if enabled else ("", None)
        return build_micron(interfaces, path, status_text, status_error)
    except Exception as e:
        return f"Couldn't read the LoRa settings ({type(e).__name__}: {esc(e)})."


if __name__ == "__main__":
    print(get_lora_micron())
