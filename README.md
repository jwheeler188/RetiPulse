# RetiPulse

A live LoRa status page for your NomadNet node. RetiPulse shows whether your RNode radio is up, how busy the channel is, and the radio settings it's configured with, read fresh from Reticulum every time the page loads.

Here's roughly what visitors see. In a NomadNet client, Online and Up are green, and Offline and Down are red:

```
LoRa Status

                    LoRa Online
   Settings from the Reticulum config, last changed 4:43PM 09/25/2026

  My-RNode
  Status            Up  (Gateway)
  Rate              878.91 bps
  Noise floor       -129 dBm
  Interference      -116 dBm 18s ago
  Airtime           0.0% (15s), 1.94% (1h)
  Channel load      0.0% (15s), 2.73% (1h)
  Traffic           ↑7.20 KB 0 bps
                    ↓0 B 0 bps

  Configured settings
  Frequency         917.875 MHz
  Bandwidth         62.5 kHz
  Spreading factor  SF9
  Coding rate       4/5
  TX power          27 dBm
  Est. bitrate      879 bps

  [[My-RNode]]
    frequency = 917875000
    bandwidth = 62500
    ...
```

## Features

- Live status for every enabled RNode radio from `rnstatus`: up or down, mode, rate, noise floor, interference, airtime, channel load, and traffic.
- Configured settings from the Reticulum config: frequency, bandwidth, spreading factor, coding rate, TX power, and an estimated on-air bitrate, plus the settings in config-file format for anyone setting up a compatible radio.
- A clear banner at the top: **LoRa Online**, **LoRa Offline**, or **LoRa status unknown**.
- Always current. The page reads the config and runs `rnstatus` on every load, so a settings change shows up on the next visit. No cron job or cache.
- Safe to publish. Only settings on an approved list are shown, so IFAC network names, passphrases, and serial ports in your config are never printed.
- Python standard library only. Nothing to `pip install`, and no internet access needed.

## Requirements

- A NomadNet node, installed and running
- Reticulum with at least one `RNodeInterface` in its config
- `rnstatus` (installed with Reticulum) for live status
- Python 3.9 or newer
- NomadNet and Reticulum running as the same user, so the page can read the config and run `rnstatus`

## Install options

There are two ways to install RetiPulse. Both give the same result:

- **Quick install:** run `install.sh`, which finds your config and `rnstatus` and does everything for you. Best for most people.
- **Manual install:** copy the files and set things up by hand. Use this if you want to see every step before it happens, or if your setup is unusual.

Either way, install as the same user that runs NomadNet. Installing doesn't need `sudo`, though restarting a system-wide NomadNet service afterward may.

## Quick install

Run as the same user that runs NomadNet:

```
git clone https://github.com/jwheeler188/RetiPulse
cd retipulse
./install.sh
```

### What the installer does

1. Checks for Python 3.9+ and your NomadNet pages folder (`~/.nomadnetwork/storage/pages`).
2. Finds your Reticulum config and `rnstatus`, and warns you if either is missing.
3. Installs `retipulse.py` in `~/scripts` with your full Python path and the full path to `rnstatus`. NomadNet runs pages without your login `PATH`, so saving the full path makes sure the page can find `rnstatus`.
4. Installs the page as `retipulse.mu`. If you already have an unrelated page with that name, it's backed up to `~/scripts` first.
5. Runs the page once and shows you what it will display.

### Installer options

Set any of these before `./install.sh` to change how it runs:

| Option | Default | What it does |
| --- | --- | --- |
| `SCRIPTS_DIR` | `~/scripts` | Where `retipulse.py` goes |
| `PAGES_DIR` | `~/.nomadnetwork/storage/pages` | Your NomadNet pages folder |
| `PYTHON` | output of `which python3` | Python to use (3.9 or newer) |

For example:

```
PYTHON=/usr/bin/python3 SCRIPTS_DIR=~/retipulse-files ./install.sh
```

It's safe to run the installer again, for example after updating the repo. It updates the page and script in place.

### Restart NomadNet

NomadNet registers its pages when it starts, so restart it after installing to make sure the new page is picked up. If NomadNet runs as a systemd service:

```
sudo systemctl restart nomadnet
```

Use your own unit name if it's different (check with `systemctl list-units | grep -i nomad`), or `systemctl --user restart nomadnet` for a user service. If you start NomadNet by hand, stop it and start it again.

### Link to it

Visit `/page/retipulse.mu` on your node to check the page, then add a link from your home page or menu:

```
`[LoRa Status`:/page/retipulse.mu]
```

## Manual install

To do the same steps by hand from the repo folder, as the NomadNet user:

1. Copy the script:
   ```
   mkdir -p ~/scripts
   cp scripts/retipulse.py ~/scripts/
   chmod +x ~/scripts/retipulse.py
   ```
2. Find the full paths to Python and `rnstatus`. Python must be version 3.9 or newer:
   ```
   which python3
   python3 --version
   which rnstatus
   ```
3. Edit `~/scripts/retipulse.py` and set `RNSTATUS_PATH` to the full `rnstatus` path from step 2, for example `RNSTATUS_PATH = "/home/<user>/.local/bin/rnstatus"`.
4. Put your Python path on the first line of `pages/retipulse.mu`, in the form `#!/usr/bin/python3`, then install the page:
   ```
   cp pages/retipulse.mu ~/.nomadnetwork/storage/pages/
   chmod +x ~/.nomadnetwork/storage/pages/retipulse.mu
   ```
5. Test it. This prints what the page will show:
   ```
   ~/.nomadnetwork/storage/pages/retipulse.mu
   ```
6. Restart NomadNet, as described under [Restart NomadNet](#restart-nomadnet).

If you put the script somewhere other than `~/scripts`, also change the `SCRIPTS_DIR` line near the top of `retipulse.mu` to match.

## Files

| Path in repo | Installed to | What it is |
| --- | --- | --- |
| `scripts/retipulse.py` | `~/scripts/` | Reads the config and `rnstatus`, and formats the page |
| `pages/retipulse.mu` | `~/.nomadnetwork/storage/pages/` | The LoRa status page |

## How it works

Each time someone opens the page, RetiPulse:

1. Finds the Reticulum config the same way Reticulum does: `/etc/reticulum/config`, then `~/.config/reticulum/config`, then `~/.reticulum/config`.
2. Collects every interface with `type = RNodeInterface` that is enabled (`enabled = yes` or `interface_enabled = true`). Like Reticulum, it treats an interface with neither setting as off.
3. Runs `rnstatus` and matches each radio by name, using the `RNodeInterface[Name]` lines in its output.
4. Picks the banner:
    - **LoRa Online**: at least one enabled radio reports `Status : Up`.
    - **LoRa Offline**: no RNode interface is enabled, or none of the enabled ones is up. A radio missing from `rnstatus` entirely usually means `rnsd` isn't running.
    - **LoRa status unknown**: `rnstatus` couldn't be run, so only the configured settings are shown.

The page shows the settings in the config file, not necessarily what the radio is running. Reticulum applies config changes when it restarts, so between editing the config and restarting `rnsd`, the page shows the new settings before the radio uses them.

## Privacy

Your Reticulum config can hold things you don't want public, like IFAC network names and passphrases. RetiPulse only ever shows items on two approved lists at the top of `retipulse.py`:

- `SAFE_KEYS`: config settings, such as `frequency`, `bandwidth`, `spreadingfactor`, `codingrate`, `txpower`, and `mode`
- `LIVE_KEYS`: `rnstatus` lines, such as Status, Rate, Noise Fl., Airtime, and Ch. Load

Everything else is left out, including serial ports and any other interfaces. To show another setting, add its name to the matching list.

## Match your site's header and menu

If your pages share a common header and menu, the RetiPulse page can show them too. Create `site_parts.py` in your scripts folder (`~/scripts` by default) with a `print_top()` function that prints them:

```python
# ~/scripts/site_parts.py
import os

def print_top():
    for name in ("my_header.mu", "my_menu.mu"):
        with open(os.path.expanduser("~/scripts/" + name), encoding="utf-8") as f:
            print(f.read(), end="")
```

The RetiPulse page looks for `site_parts.py` every time it loads and, if it's there, prints your header and menu above its own content. Because the hook lives in your own file, it keeps working when you rerun the installer or update RetiPulse. If `site_parts.py` doesn't exist, the page shows its own content only.

## Configuration

Settings are at the top of `retipulse.py`. The installer sets `RNSTATUS_PATH` for you.

| Setting | Default | What it does |
| --- | --- | --- |
| `CONFIG_PATH` | `None` | Reticulum config to read; `None` finds it the way Reticulum does |
| `LORA_TYPES` | `("RNodeInterface",)` | Interface types treated as LoRa radios |
| `SHOW_CONFIG_BLOCK` | `True` | Also show settings in config-file format |
| `RNSTATUS_PATH` | `None` | Full path to `rnstatus`; `None` searches your `PATH` and `~/.local/bin` |
| `RNSTATUS_TIMEOUT` | `10` | Seconds to wait for `rnstatus` |
| `SAFE_KEYS` | see [Privacy](#privacy) | Config settings allowed on the page |
| `LIVE_KEYS` | see [Privacy](#privacy) | `rnstatus` lines allowed on the page, and their labels |

## Troubleshooting

Run the page by hand, the same way NomadNet does. Errors print here but not in the client:

```
~/.nomadnetwork/storage/pages/retipulse.mu
```

| Symptom | Fix |
| --- | --- |
| Client says "No content available" | Run the page by hand (above) to see the error |
| Page shows the script's code | `chmod +x ~/.nomadnetwork/storage/pages/retipulse.mu` |
| Page doesn't show up at all | Restart NomadNet (see [Restart NomadNet](#restart-nomadnet)) |
| "LoRa status unknown" | `rnstatus` wasn't found or timed out; set `RNSTATUS_PATH` to its full path (`which rnstatus`) |
| "LoRa Offline" but the radio is working | Check that `rnstatus` lists `RNodeInterface[Name]` with the same name as the `[[Name]]` section in your config |
| "No LoRa interfaces are enabled" but one is | Make sure the interface has `type = RNodeInterface` and `enabled = yes` (or `interface_enabled = true`) |
| "Can't read the Reticulum config" | NomadNet must run as the same user as Reticulum, or set `CONFIG_PATH` to a config that user can read |
| A setting you want isn't shown | Add its name to `SAFE_KEYS` in `retipulse.py` |

## Uninstall

```
rm ~/.nomadnetwork/storage/pages/retipulse.mu
rm ~/scripts/retipulse.py
```

Then remove any links to `/page/retipulse.mu` from your other pages, and restart NomadNet.

## See also

- [RetiCast](<RetiCast repo URL>): live weather and NWS alerts for your grid square, on your NomadNet pages.
- [RetiSkip](<RetiSkip repo URL>): HF band conditions and solar data as a ready-to-install NomadNet page.
