#!/usr/bin/python3
# retipulse.mu - RetiPulse: live LoRa status page for NomadNet.
# The first line must be the full path to your Python (run: which python3).
import os
import sys

SCRIPTS_DIR = os.path.expanduser("~/scripts")
sys.path.insert(0, SCRIPTS_DIR)

# Match the rest of your site: if SCRIPTS_DIR has a site_parts.py with a
# print_top() function, it prints your own header and menu above this page.
try:
    from site_parts import print_top
    print_top()
except ImportError:
    pass
except Exception as e:
    print(f"`Ff00[site header error: {type(e).__name__}]`f")

try:
    from retipulse import get_lora_micron
    body = get_lora_micron()
except Exception as e:
    body = f"LoRa status unavailable ({type(e).__name__})"

print(">LoRa Status")
print()
print(body)
print()
print("`[Back to home`:/page/index.mu]")
