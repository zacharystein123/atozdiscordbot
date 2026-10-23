# AtoZDiscordBot

Webhook alerts for jobs on hiring.amazon.com (A to Z).

One-pass Selenium script that opens the Amazon hiring search for ZIP 33545, reads each job card, and posts a Discord embed to the matching facility channel. When the card also names a shift type, it posts the same embed to that shift channel.

## Facilities

* Grocery (UFL5)
* Robotics (TPA4), also the fallback when a card has no facility code
* Fulfillment (SFL4)
* Sortation (TPA5)
* Delivery (DTP9)

## Shift channels

Reduced Time, Part Time, Full Time, and Flex Time.

## Setup

Python 3.8+ and Google Chrome are required.

```bash
pip install -r requirements.txt
cp config.example.json config.json
```

Put each Discord webhook in `config.json`. That file stays on your machine. `config.example.json` has the facility names, role ids, and ZIP, with the webhook fields left blank.

Run one check:

```bash
python atozjobsdiscord.py
```

Set `ATOZ_CONFIG` if the config file lives somewhere other than `config.json` next to the script.
