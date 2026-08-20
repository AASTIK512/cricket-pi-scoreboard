#!/usr/bin/env python3
"""Cricket Scoreboard for Raspberry Pi 3.

A lightweight local Tkinter app built from the supplied Cricbuzz scripts.
"""
from __future__ import annotations

import html
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

import requests
from bs4 import BeautifulSoup

LIVE_URL = "https://www.cricbuzz.com/cricket-match/live-scores"
SCHEDULE_URL = "https://www.cricbuzz.com/cricket-schedule/upcoming-series/international"
NEWS_URL = "https://eventregistry.org/api/v1/article/getArticles"
HEADERS = {"User-Agent": "Mozilla/5.0 (Raspberry Pi Cricket Scoreboard)"}
TIMEOUT = 15


def get_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_live_matches() -> list[str]:
    soup = get_soup(LIVE_URL)
    items = soup.find_all("div", class_="cb-scr-wll-chvrn cb-lv-scrs-col")
    values = [" ".join(item.get_text(" ", strip=True).split()) for item in items]
    return values or ["No live matches found right now."]


def get_schedule() -> list[str]:
    soup = get_soup(SCHEDULE_URL)
    results: list[str] = []
    for container in soup.find_all("div", class_="cb-col-100 cb-col"):
        date = container.find("div", class_="cb-lv-grn-strip text-bold")
        detail = container.find("div", class_="cb-col-100 cb-col")
        if date and detail:
            text = f"{date.get_text(' ', strip=True)} — {detail.get_text(' ', strip=True)}"
            text = " ".join(text.split())
            if text not in results:
                results.append(text)
    return results or ["No upcoming international matches found."]


def get_news() -> list[dict[str, str]]:
    """Return recent cricket headlines from NewsAPI.ai / Event Registry."""
    api_key = os.environ.get("NEWSAPI_AI_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set NEWSAPI_AI_KEY before using the News tab.")
    payload = {
        "apiKey": api_key,
        "keyword": "cricket",
        "keywordSearchMode": "simple",
        "lang": "eng",
        "articlesPage": 1,
        "articlesCount": 15,
        "articlesSortBy": "date",
        "articlesSortByAsc": False,
        "resultType": "articles",
    }
    response = requests.post(NEWS_URL, json=payload, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    body = response.json()
    raw_articles = body.get("articles", {}).get("results", [])
    news: list[dict[str, str]] = []
    for article in raw_articles:
        source = article.get("source", {}) or {}
        news.append({
            "title": html.unescape(article.get("title", "Untitled")),
            "source": source.get("title", source.get("uri", "Unknown source")),
            "date": article.get("dateTime", article.get("date", "")),
            "url": article.get("url", ""),
        })
    return news or [{"title": "No cricket news found.", "source": "NewsAPI.ai", "date": "", "url": ""}]


def find_player_stats(player_name: str) -> dict[str, Any]:
    """Fetch a player profile through Cricbuzz search results.

    googlesearch-python is optional. If unavailable, the UI reports a useful
    installation message rather than crashing.
    """
    try:
        from googlesearch import search
    except ImportError as exc:
        raise RuntimeError("Install googlesearch-python to use player search.") from exc

    profile_link = None
    for link in search(f"{player_name} cricbuzz", num_results=5):
        if "cricbuzz.com/profiles/" in link:
            profile_link = link
            break
    if not profile_link:
        raise RuntimeError("No Cricbuzz player profile found.")

    soup = get_soup(profile_link)
    profile = soup.find("div", id="playerProfile")
    if not profile:
        raise RuntimeError("The player profile format could not be read.")
    panel = profile.find("div", class_="cb-col cb-col-100 cb-bg-white") or profile
    name_node = panel.find("h1", class_="cb-font-40")
    country_node = panel.find("h3", class_="cb-font-18 text-gray")
    personal = soup.find_all("div", class_="cb-col cb-col-60 cb-lst-itm-sm")
    rankings = soup.find_all("div", class_="cb-col cb-col-25 cb-plyr-rank text-right")
    summaries = soup.find_all("div", class_="cb-plyr-tbl")
    data: dict[str, Any] = {
        "name": name_node.get_text(strip=True) if name_node else player_name.title(),
        "country": country_node.get_text(strip=True) if country_node else "Unknown",
        "role": personal[2].get_text(" ", strip=True) if len(personal) > 2 else "Unknown",
        "rankings": {}, "batting_stats": {}, "bowling_stats": {},
    }
    ranking_values = [x.get_text(" ", strip=True) for x in rankings]
    data["rankings"] = {
        "batting": dict(zip(("Test", "ODI", "T20"), ranking_values[:3])),
        "bowling": dict(zip(("Test", "ODI", "T20"), ranking_values[3:6])),
    }
    for index, key in ((0, "batting_stats"), (1, "bowling_stats")):
        if index >= len(summaries) or not summaries[index].find("tbody"):
            continue
        for row in summaries[index].find("tbody").find_all("tr"):
            cols = row.find_all("td")
            if not cols:
                continue
            fmt = cols[0].get_text(strip=True)
            if key == "batting_stats" and len(cols) > 12:
                data[key][fmt] = {"Matches": cols[1].get_text(strip=True), "Runs": cols[3].get_text(strip=True), "Highest": cols[5].get_text(strip=True), "Average": cols[6].get_text(strip=True), "Strike rate": cols[7].get_text(strip=True), "100s": cols[12].get_text(strip=True), "50s": cols[11].get_text(strip=True)}
            elif key == "bowling_stats" and len(cols) > 11:
                data[key][fmt] = {"Balls": cols[3].get_text(strip=True), "Runs": cols[4].get_text(strip=True), "Wickets": cols[5].get_text(strip=True), "Best": cols[9].get_text(strip=True), "Economy": cols[7].get_text(strip=True), "5 wickets": cols[11].get_text(strip=True)}
    return data


class CricketApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cricket Scores")
        self.geometry("900x600")
        self.minsize(700, 450)
        self.configure(bg="#0b1320")
        self.tasks: queue.Queue[tuple[str, Any, Exception | None]] = queue.Queue()
        self._build_style()
        self._build_ui()
        self.after(100, self._poll_tasks)
        self.refresh_live()
        self.refresh_schedule()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#0b1320")
        style.configure("TLabel", background="#0b1320", foreground="#edf2f7", font=("DejaVu Sans", 12))
        style.configure("Title.TLabel", font=("DejaVu Sans", 24, "bold"), foreground="#55d6be")
        style.configure("Head.TLabel", font=("DejaVu Sans", 15, "bold"), foreground="#55d6be")
        style.configure("TButton", font=("DejaVu Sans", 11, "bold"), padding=7)
        style.configure("TNotebook", background="#0b1320", borderwidth=0)
        style.configure("TNotebook.Tab", font=("DejaVu Sans", 12, "bold"), padding=(14, 8))

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(18, 15, 18, 8)); header.pack(fill="x")
        ttk.Label(header, text="CRICKET SCORES", style="Title.TLabel").pack(side="left")
        self.status = ttk.Label(header, text="Connecting…", foreground="#a0aec0"); self.status.pack(side="right")
        self.tabs = ttk.Notebook(self); self.tabs.pack(fill="both", expand=True, padx=14, pady=8)
        self.live_tab = self._text_tab("Live Matches", self.refresh_live)
        self.schedule_tab = self._text_tab("Upcoming Schedule", self.refresh_schedule)
        self.news_tab = self._text_tab("News", self.refresh_news)
        self.player_tab = ttk.Frame(self.tabs, padding=16); self.tabs.add(self.player_tab, text="Player Stats")
        search_row = ttk.Frame(self.player_tab); search_row.pack(fill="x")
        self.player_entry = ttk.Entry(search_row, font=("DejaVu Sans", 13)); self.player_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.player_entry.insert(0, "Virat Kohli")
        ttk.Button(search_row, text="SEARCH", command=self.refresh_player).pack(side="right")
        self.player_output = self._output(self.player_tab); self.player_output.pack(fill="both", expand=True, pady=(14, 0))

    def _output(self, parent: ttk.Frame) -> tk.Text:
        text = tk.Text(parent, bg="#111c2d", fg="#edf2f7", insertbackground="white", relief="flat", wrap="word", font=("DejaVu Sans", 13), padx=14, pady=12)
        text.configure(state="disabled"); return text

    def _text_tab(self, title: str, callback: Any) -> tk.Text:
        frame = ttk.Frame(self.tabs, padding=16); self.tabs.add(frame, text=title)
        ttk.Button(frame, text="REFRESH", command=callback).pack(anchor="e", pady=(0, 10))
        output = self._output(frame); output.pack(fill="both", expand=True)
        if title.startswith("Live"): self.live_output = output
        elif title.startswith("Upcoming"): self.schedule_output = output
        else: self.news_output = output
        return output

    def _set_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state="normal"); widget.delete("1.0", "end"); widget.insert("end", content); widget.configure(state="disabled")

    def _run(self, kind: str, fn: Any, *args: Any) -> None:
        self.status.configure(text="Updating…")
        threading.Thread(target=self._worker, args=(kind, fn, args), daemon=True).start()

    def _worker(self, kind: str, fn: Any, args: tuple[Any, ...]) -> None:
        try: self.tasks.put((kind, fn(*args), None))
        except Exception as exc: self.tasks.put((kind, None, exc))

    def _poll_tasks(self) -> None:
        try:
            while True:
                kind, result, error = self.tasks.get_nowait()
                if error: messagebox.showerror("Could not update", str(error))
                elif kind == "live": self._set_text(self.live_output, "\n\n".join(f"LIVE MATCH {i}:\n{v}" for i, v in enumerate(result, 1)))
                elif kind == "schedule": self._set_text(self.schedule_output, "\n\n".join(f"{i}. {v}" for i, v in enumerate(result, 1)))
                elif kind == "news":
                    self._set_text(self.news_output, "\n\n".join(f"{i}. {item['title']}\n   {item['source']}  {item['date']}\n   {item['url']}" for i, item in enumerate(result, 1)))
                elif kind == "player": self._show_player(result)
                self.status.configure(text="Updated")
        except queue.Empty: pass
        self.after(100, self._poll_tasks)

    def _show_player(self, data: dict[str, Any]) -> None:
        lines = [f"{data['name']}  |  {data['country']}", f"Role: {data['role']}", "", "RANKINGS"]
        for group, values in data["rankings"].items(): lines.append(f"{group.title()}: " + "   ".join(f"{k} {v}" for k, v in values.items()))
        for group, values in (("Batting", data["batting_stats"]), ("Bowling", data["bowling_stats"])):
            lines += ["", f"{group.upper()} STATS"]
            for fmt, stats in values.items(): lines.append(f"{fmt}: " + " | ".join(f"{k}: {v}" for k, v in stats.items()))
        self._set_text(self.player_output, "\n".join(lines))

    def refresh_live(self) -> None: self._run("live", get_live_matches)
    def refresh_schedule(self) -> None: self._run("schedule", get_schedule)
    def refresh_news(self) -> None: self._run("news", get_news)
    def refresh_player(self) -> None:
        name = self.player_entry.get().strip()
        if name: self._run("player", find_player_stats, name)


if __name__ == "__main__":
    CricketApp().mainloop()
