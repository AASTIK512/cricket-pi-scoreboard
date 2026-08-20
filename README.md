# Cricket Scores for Raspberry Pi 3

This is a lightweight local desktop application for Raspberry Pi 3. It provides three screens: live cricket matches, upcoming international fixtures, and searchable player statistics. The interface uses Tkinter, so it is suitable for a Pi connected to a monitor or touchscreen.

The app fetches public cricket information from Cricbuzz when the **Refresh** buttons are pressed. An internet connection is required for fresh scores; the app itself runs locally on the Raspberry Pi.

## Installation

On Raspberry Pi OS, open a terminal and run:

```bash
sudo apt update
sudo apt install -y python3-tk python3-pip
cd ~/cricket_pi_app
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Before starting the app, configure the NewsAPI.ai key in the shell:

```bash
export NEWSAPI_AI_KEY="your-newsapi-ai-key"
python3 app.py
```

For the included launcher, create a local file named `newsapi.env` containing:

```text
NEWSAPI_AI_KEY=your-newsapi-ai-key
```

Keep this file private; it is intentionally not included in the project archive. The News tab uses NewsAPI.ai/Event Registry's `getArticles` endpoint and requests recent English cricket headlines. If the key is missing or the account limit is reached, the app shows an error without closing.

If the project is copied to another directory, replace `~/cricket_pi_app` with that directory. For player search, the `googlesearch-python` package is included in `requirements.txt`; live matches and schedules only require `requests` and `beautifulsoup4`.

## Start from the desktop

The `start_cricket_scores.sh` launcher can be double-clicked from the file manager after enabling execution permission:

```bash
chmod +x start_cricket_scores.sh
```

To start it automatically after the Pi logs in, add the following command to the desktop session's autostart configuration:

```text
/home/pi/cricket_pi_app/start_cricket_scores.sh
```

Change `/home/pi` if the project is installed under a different username.

## Notes

Cricbuzz may change its page layout or restrict automated requests. NewsAPI.ai also applies token and rate limits to API requests, so use the News tab's refresh button only when needed.

Cricbuzz may change its page layout or restrict automated requests. The application catches request failures and displays an error instead of closing. The supplied scripts were refactored so that network requests occur only when a user refreshes a screen, and the Tkinter interface remains responsive while data is being fetched.
