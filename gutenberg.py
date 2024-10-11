import csv
import datetime
import json
import os
from pathlib import Path

import requests

from references import CONTENT_TYPES, ISO_LANG_CODES

ID = "id"
TITLE = "title"
LANGUAGES = "languages"
COPYRIGHT = "copyright"
DOWNLOAD_COUNT = "download_count"
DATE = "date"
URL = "url"
AUTHORS = "authors"
INTERNAL_ID = "internal_id"
FORMATS = "formats"

FILE_NAME = "file_name"
FILE_URL = "file_url"
FORMAT = "format"
FILE_SIZE = "file_size"

HEADERS = [ID, INTERNAL_ID, LANGUAGES, TITLE, AUTHORS, COPYRIGHT, DOWNLOAD_COUNT, DATE, URL]
HEADERS_EXTENDED = [ID, INTERNAL_ID, LANGUAGES, TITLE, AUTHORS, COPYRIGHT,
                    DOWNLOAD_COUNT, DATE, FILE_URL, FILE_NAME, FILE_SIZE, FORMAT]

ISBN_LANG_GROUP = {
    "en": "0",
    "fr": "2",
    "fi": "951",
    "de": "3",
}

BASE_DIR = Path(__file__).resolve().parent
BASE_URL = "https://gutendex.com/books"

BOOK_FOLDER = os.path.join(BASE_DIR, "gutenberg_books")


session = requests.session()


def get_top_languages(session, size=10):
    """Get top {size} languages by number of books"""
    langs_ranking = dict()
    for lang in ISO_LANG_CODES:
        response = session.get(BASE_URL, params={LANGUAGES: lang})
        count = response.json()["count"]
        if count > 0:
            langs_ranking[lang] = count
    print(f"Total languages available: {len(langs_ranking)}")
    ranked = [[key, val] for key, val in sorted(langs_ranking.items(), key=lambda item: item[1], reverse=True)]
    print(ranked[:size])


def get_first_books_ids(lang, num_books=2):
    """Get ids of the first {num_books}"""
    print(lang)
    response = session.get("https://gutendex.com/books", params={LANGUAGES: lang, COPYRIGHT: "true"})
    data = response.json()["results"]
    for entry in data[:num_books]:
        print(entry[ID])


def get_tops_for_langs(langs=("en", "fr", "fi", "de")):
    """Get IDs for the first books for given languages"""
    for lang in langs:
        get_first_books_ids(lang)


def create_internal_id(lang, gb_id):
    """Generate an example code"""
    return f"{ISBN_LANG_GROUP[lang]}{gb_id}"


def get_book_data(book_id, extended=False, session=session):
    """API docs: https://gutendex.com/"""
    response = session.get(url=f"{BASE_URL}/{book_id}/")
    entry = response.json()
    book_urls = entry[FORMATS]
    first_available = list(book_urls.keys())[0]
    lang = entry[LANGUAGES][0]

    row = {
        ID: entry[ID],
        INTERNAL_ID: create_internal_id(lang, gb_id=entry[ID]),
        TITLE: entry[TITLE],
        LANGUAGES: lang,
        COPYRIGHT: entry[COPYRIGHT],
        DOWNLOAD_COUNT: entry[DOWNLOAD_COUNT],
        DATE: str(datetime.date.today()),
        AUTHORS: ", ".join([author["name"] for author in entry[AUTHORS]])
    }
    if extended:
        row[FORMATS] = book_urls
    else:
        row[URL] = book_urls[first_available]
    print(row)
    return row


def extend_rows(book_id, row):
    """Incorporate file metadata into a row describing a book"""
    formats = row.pop(FORMATS, [])
    for key in formats:
        data = get_file_meta(book_id, key, formats[key])
        if data is not None:
            data.update(row)
            yield data


def extend_dicts(book_id, row):
    """Add files metadata to book"""
    formats = row.pop(FORMATS, [])
    results = list()
    for key in formats:
        data = get_file_meta(book_id, key, formats[key])
        if data is not None:
            results.append(data)
    row[FORMATS] = results
    return row


def write_csv(book_ids, extended=False):
    """Write data as CSV
    If extended, writes a row for each available file. Otherwise a row for a book"""
    if extended:
        headers = HEADERS_EXTENDED
    else:
        headers = HEADERS
    with open('gutenberg_downloads.csv', 'w', newline='') as handler:
        writer = csv.DictWriter(handler, fieldnames=headers)
        writer.writeheader()
        for book_id in book_ids:
            # Grab meta for one book
            result = get_book_data(book_id, extended=extended)
            if extended:
                for row in extend_rows(book_id=book_id, row=result):
                    writer.writerow(row)
            else:
                writer.writerow(result)
    print("DONE")


def write_json(book_ids):
    """Write data as json"""
    data = list()
    for book_id in book_ids:
        data.append(extend_dicts(book_id, get_book_data(book_id, extended=True)))
    with open("gutenberg_downloads.json", 'w', encoding="utf-8") as handler:
        json.dump(data, handler, ensure_ascii=False, indent=2)
    print("DONE")


def download_file(fpath, url):
    """Download a file if it is not yet there.
    The only practical purpose being that it's the easiest way to grab its size"""
    response = session.get(url)
    with open(fpath, mode="wb") as handler:
        handler.write(response.content)
        print(f"---> Downloaded to {fpath}")


def get_file_meta(book_id, content_type, file_url):
    """Grab files metadata to extend the info aboot books"""
    if content_type in ["image/jpeg", "application/octet-stream"]:
        return
    ext = CONTENT_TYPES.get(content_type)
    if ext is None:
        return
    if not os.path.isdir(BOOK_FOLDER):
        os.mkdir(BOOK_FOLDER)
    fname = f"pg{book_id}.{ext.lower()}"
    fpath = os.path.join(BOOK_FOLDER, fname)
    if not os.path.exists(fpath):
        download_file(fpath=fpath, url=file_url)
    return {
        FILE_URL: file_url,
        FORMAT: ext,
        FILE_NAME: fname,
        FILE_SIZE: os.path.getsize(fpath)
    }


if __name__ == '__main__':
    # get_data({LANGUAGES: "de"})
    # get_top_languages(session=session)
    # get_tops_for_langs()
    book_ids = [84, 7849, 2650, 17489, 14774, 7000, 31284, 5740]
    write_csv(book_ids)
    # write_json(book_ids)
    # print(BOOK_FOLDER)
    # print(get_file_meta(2650, "text/plain; charset=utf-8", "https://www.gutenberg.org/files/2650/2650-0.txt"))
