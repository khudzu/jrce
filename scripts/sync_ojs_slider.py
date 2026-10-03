#!/usr/bin/env python3
"""Update the static Swiper cards from the public OJS homepage."""
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

SOURCE = 'https://ejournal.uin-malang.ac.id/index.php/jrce/index'
ROOT = Path(__file__).resolve().parents[1]


def sync():
    request = Request(SOURCE, headers={'User-Agent': 'JRCE-slider-sync/1.0'})
    with urlopen(request, timeout=45) as response:
        soup = BeautifulSoup(response.read(), 'html.parser')
    cards = soup.select('.jrce-issue-slider .jrce-slider-track .swiper-slide')
    if not cards:
        raise ValueError('OJS slider is empty; existing website is preserved')
    rendered = []
    seen = set()
    for card in cards:
        link = card.select_one('a[href]')
        image = card.select_one('img[src]')
        volume = card.select_one('.volume-info')
        date = card.select_one('.publication-date')
        if any(item is None for item in (link, image, volume, date)):
            raise ValueError('Incomplete OJS card; existing website is preserved')
        href = urljoin(SOURCE, link['href'])
        src = urljoin(SOURCE, image['src'])
        for url in (href, src):
            parsed = urlparse(url)
            if parsed.scheme != 'https' or parsed.hostname != 'ejournal.uin-malang.ac.id':
                raise ValueError('Unexpected OJS card URL')
        if href in seen:
            raise ValueError('Duplicate issue in OJS slider')
        seen.add(href)
        title = volume.get_text(' ', strip=True)
        published = date.get_text(' ', strip=True)
        if not title or not published:
            raise ValueError('Empty OJS card text')
        rendered.append(f'''<div class="swiper-slide">
    <div class="journal-card">
        <a href="{escape(href, quote=True)}">
            <img src="{escape(src, quote=True)}" alt="{escape('Cover Jurnal ' + title, quote=True)}" class="cover-image">
            <div class="card-content">
                <p class="volume-info">{escape(title)}</p>
                <p class="publication-date">{escape(published)}</p>
            </div>
        </a>
    </div>
</div>''')
    path = ROOT / 'index.html'
    original = path.read_text(encoding='utf-8')
    start_token = '<div class="swiper-wrapper">'
    end_token = '<div class="swiper-pagination"></div>'
    if original.count(start_token) != 1 or original.count(end_token) != 1:
        raise ValueError('Website slider boundaries are ambiguous')
    start = original.index(start_token) + len(start_token)
    end = original.index(end_token, start)
    updated = original[:start] + '\n' + '\n\n'.join(rendered) + '\n                    </div>\n                    ' + original[end:]
    if updated != original:
        temporary = path.with_suffix('.html.tmp')
        temporary.write_text(updated, encoding='utf-8')
        temporary.replace(path)
    print(f'Synchronized {len(rendered)} issues from OJS')


if __name__ == '__main__':
    sync()
