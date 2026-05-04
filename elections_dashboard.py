import curses
import time
import subprocess
import requests
from bs4 import BeautifulSoup

URL = "https://results.eci.gov.in/ResultAcGenMay2026/index.htm"

REFRESH_INTERVAL = 180   # 3 min (safe)
DRAW_INTERVAL = 0.1      # UI refresh only

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
    import os
    soup = BeautifulSoup(html, "html.parser")
    result = []

    for box in soup.select(".asmb-box"):
        img = box.select_one(".asmb-title img")

        state = "Unknown"
        if img:
            if img.has_attr("alt") and img["alt"].strip():
                state = img["alt"].strip()
            else:
                src = img.get("src", "")
                name = os.path.basename(src).replace(".svg", "")
                state = name.replace("-", " ").title()

        parties = []
        for row in box.select(".pr-row"):
            cols = row.find_all("div")
            if len(cols) >= 3:
                parties.append(
                    (cols[0].text.strip(),
                     cols[1].text.strip(),
                     cols[2].text.strip())
                )

        result.append((state, parties))

    return result


def fetch_data():
    html = fetch_html()
    if not html:
        return [("ERROR", [("fetch failed", "-", "-")])]
    return parse(html)


def draw(stdscr, data, last_update):
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    stdscr.addstr(0, 0, "Election TUI | r=refresh q=quit")
    stdscr.addstr(1, 0, f"Last update: {last_update}")

    # grid layout
    col_width = 30
    cols = max(1, w // col_width)

    y_offset = 3

    for idx, (state, parties) in enumerate(data):
        col = idx % cols
        row = idx // cols

        x = col * col_width
        y = y_offset + row * 8   # each block height

        if y >= h - 2:
            break

        stdscr.addstr(y, x, f"[{state}]")

        for i, (p, l, w_) in enumerate(parties[:5]):
            if y + i + 1 >= h:
                break
            line = f"{p[:10]:<10} L:{l:>3} W:{w_:>3}"
            stdscr.addstr(y + i + 1, x, line)

    stdscr.refresh()


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)

    data = fetch_data()
    last_update = time.strftime("%H:%M:%S")

    last_fetch = time.time()
    last_draw = 0

    while True:
        now = time.time()

        # draw often (cheap)
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

        # fetch only every 3 min
        if now - last_fetch > REFRESH_INTERVAL:
            data = fetch_data()
            last_update = time.strftime("%H:%M:%S")
            last_fetch = now

        time.sleep(0.05)


if __name__ == "__main__":
    curses.wrapper(main)
