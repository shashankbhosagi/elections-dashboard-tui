import curses
import time
import subprocess
import requests
from bs4 import BeautifulSoup
import os

URL = "https://results.eci.gov.in/ResultAcGenMay2026/index.htm"

REFRESH_INTERVAL = 180
DRAW_INTERVAL = 0.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
}


def fetch_html():
    try:
        r = requests.get(URL, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.text
    except:
        pass

    try:
        out = subprocess.check_output(
            ["curl", "-s", "-L", "-A", "Mozilla/5.0", URL]
        )
        return out.decode()
    except:
        return None


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    result = []

    for box in soup.select(".asmb-box"):
        # ---- state name ----
        img = box.select_one(".asmb-title img")
        state = "Unknown"

        if img:
            if img.has_attr("alt") and img["alt"].strip():
                state = img["alt"].strip()
            else:
                src = img.get("src", "")
                name = os.path.basename(src).replace(".svg", "")
                state = name.replace("-", " ").title()

        # ---- seats (counted/total or total only) ----
        total = 0
        counted = 0

        label = box.find("span", string=lambda s: s and "Assembly Constituencies" in s)
        if label:
            parent = label.find_parent("li")
            spans = parent.find_all("span")

            if len(spans) >= 2:
                raw = spans[1].text.strip()

                if "/" in raw:
                    try:
                        counted, total = map(int, raw.split("/"))
                    except:
                        counted, total = 0, 0
                else:
                    try:
                        total = int(raw)
                        counted = total
                    except:
                        total, counted = 0, 0

        majority = total // 2 + 1 if total else 0

        # ---- parties ----
        parties = []
        for row in box.select(".pr-row"):
            cols = row.find_all("div")
            if len(cols) >= 3:
                try:
                    parties.append(
                        (
                            cols[0].text.strip(),
                            int(cols[1].text.strip()),
                            int(cols[2].text.strip()),
                        )
                    )
                except:
                    continue

        result.append((state, total, counted, majority, parties))

    return result


def fetch_data():
    html = fetch_html()
    if not html:
        return [("ERROR", 0, 0, 0, [("fetch failed", 0, 0)])]
    return parse(html)


def draw(stdscr, data, last_update):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    stdscr.addstr(0, 0, "Election TUI | r=refresh q=quit")
    stdscr.addstr(1, 0, f"Last update: {last_update}")

    col_width = 34
    cols = max(1, w // col_width)

    y_offset = 3

    for idx, (state, total, counted, majority, parties) in enumerate(data):
        col = idx % cols
        row = idx // cols

        x = col * col_width
        y = y_offset + row * 9

        if y >= h - 2:
            break

        # ---- header ----
        stdscr.addstr(y, x, f"[{state}]")
        stdscr.addstr(y + 1, x, f"Seats:{counted}/{total} Maj:{majority}")

        # ---- parties ----
        for i, (p, l, w_) in enumerate(parties[:5]):
            if y + i + 2 >= h:
                break
            stdscr.addstr(y + i + 2, x, f"{p[:10]:<10} L:{l:>3} W:{w_:>3}")

    stdscr.noutrefresh()
    curses.doupdate()


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)

    data = fetch_data()
    last_update = time.strftime("%H:%M:%S")

    last_fetch = time.time()
    last_draw = 0

    while True:
        now = time.time()

        if now - last_draw > DRAW_INTERVAL:
            draw(stdscr, data, last_update)
            last_draw = now

        key = stdscr.getch()

        if key == ord("q"):
            break

        if key == ord("r"):
            data = fetch_data()
            last_update = time.strftime("%H:%M:%S")
            last_fetch = now

        if now - last_fetch > REFRESH_INTERVAL:
            data = fetch_data()
            last_update = time.strftime("%H:%M:%S")
            last_fetch = now

        time.sleep(0.05)


if __name__ == "__main__":
    curses.wrapper(main)
