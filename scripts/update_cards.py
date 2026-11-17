
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

BASE = "https://dcd.aikatsu.com"
INDEX = BASE + "/encore/cardlist/"
FILE = Path("cards.json")

PATTERN = re.compile(
    r"(E\d+-\d{2,3}|EP-\d{3})"
    r"_(PR|ER|R|N)(_p\d+)?",
    re.I
)

def download(url):
    request = Request(url, headers={
        "User-Agent": "Mozilla/5.0"
    })
    with urlopen(request, timeout=25) as response:
        return response.read().decode(
            "utf-8", errors="replace"
        )

def find_cards(html):
    soup = BeautifulSoup(html, "html.parser")
    found = {}

    for tag in soup.find_all(["img", "source", "a"]):
        links = []

        for attr in ("src", "data-src", "href"):
            if tag.get(attr):
                links.append(tag.get(attr))

        for link in links:
            url = urljoin(BASE, link)
            path = urlparse(url).path

            if "/images/cardlist/card/" not in path:
                continue

            if "_back" in path or "_ura" in path:
                continue

            match = PATTERN.search(path)
            if not match:
                continue

            number, rarity, variant = match.groups()
            code = match.group(0)

            if number.startswith("EP-"):
                group = "promo"
                card_id = code
            elif variant:
                group = "parallel"
                card_id = code
            else:
                group = "normal"
                card_id = number

            found[card_id] = {
                "id": card_id,
                "number": code,
                "rarity": rarity,
                "group": group,
                "image": url
            }

    return found

def main():
    old = json.loads(FILE.read_text(
        encoding="utf-8"
    ))

    known = {card["id"] for card in old}
    discovered = {}

    urls = [INDEX]

    for edition in range(1, 9):
        series = f"629{edition:03d}"

        for display in (1, 2, 3):
            urls.append(
                INDEX + "?search=true"
                + f"&series={series}"
                + f"&display={display}&sort=1"
            )

    for series in ("629000", "629999", "0"):
        urls.append(
            INDEX + "?search=true"
            + f"&series={series}&display=3&sort=1"
        )

    for url in urls:
        try:
            html = download(url)
            discovered.update(find_cards(html))
        except Exception as error:
            print("取得失敗:", url, error)

    print("公式カード検出数:", len(discovered))

    if len(discovered) < 20:
        raise RuntimeError(
            "公式カードを十分に検出できませんでした"
        )

    additions = [
        card
        for card_id, card in discovered.items()
        if card_id not in known
    ]

    if not additions:
        print("新しいカードはありません")
        return

    old.extend(additions)

    FILE.write_text(
        json.dumps(
            old,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    print("追加したカード:", [
        card["id"] for card in additions
    ])

if __name__ == "__main__":
    main()
