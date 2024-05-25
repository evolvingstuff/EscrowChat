import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import config as conf


def extract_text(element):
    return ' '.join(element.stripped_strings)


def scrape_and_parse_data(url=conf.source_data_url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f'Failed to retrieve {url}. Status code: {response.status_code}')

    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.title.string
    print(f'{title}')
    print('================================================')
    print('')
    print('')

    paragraphs = soup.find_all('p')
    for i, p in enumerate(paragraphs, 1):
        text = extract_text(p)
        print('------------------------------------------------')
        print(f"Paragraph {i}: {text}")

        links = p.find_all('a')
        for j, link in enumerate(links, 1):
            link_text = extract_text(link)
            rel_href = link.get('href')
            abs_href = urljoin(url, rel_href)
            print(f"  Link {j}: {abs_href} - Text: {link_text}")
