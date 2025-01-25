"""
Convert HTML pages to Markdown representations with metadata included at page bottom.
"""

# imports
import json
from pathlib import Path

# packages
import lxml.html
import alea_preprocess

# constants
from config import DEFAULT_RAW_PATH, DEFAULT_MARKDOWN_PATH, DEFAULT_JSON_PATH


# get files from raw path
def get_files(raw_path: Path = DEFAULT_RAW_PATH) -> list[Path]:
    """
    Get the list of files from the raw path.
    """
    return sorted(
        [
            p
            for p in raw_path.rglob("*")
            if p.is_file() and "<title" in p.read_text(encoding="utf-8").lower()
        ]
    )


def get_data(html_buffer: str) -> dict:
    """
    Get the metadata from the HTML buffer.
    """
    # parse doc
    html_doc = lxml.html.fromstring(html_buffer)

    # get title and markdown
    data = {}

    # get title and meta
    data["title"] = lxml.html.tostring(
        html_doc.xpath(".//title").pop(), method="text", encoding="utf-8"
    ).decode()
    for meta_element in html_doc.xpath(".//meta"):
        try:
            meta_key = meta_element.attrib["property"]
            meta_value = meta_element.attrib["content"]
            data[meta_key] = meta_value
        except Exception:
            continue

    try:
        entry_content_element = html_doc.xpath("//main").pop()
    except IndexError:
        entry_content_element = html_doc.xpath("//body").pop()

    # get markdown
    data["markdown"] = alea_preprocess.parsers.html.conversion.extract_buffer_markdown(
        lxml.html.tostring(
            entry_content_element, method="html", encoding="utf-8"
        ).decode(),
        output_images=False,
        output_links=True,
    )

    return data


if __name__ == "__main__":
    for html_file in get_files():
        # parse
        file_data = get_data(html_file.read_text(encoding="utf-8"))

        # save markdown output
        output_markdown_file = DEFAULT_MARKDOWN_PATH / f"{html_file.stem}.md"
        output_markdown_file.parent.mkdir(parents=True, exist_ok=True)
        output_markdown_file.write_text(file_data["markdown"], encoding="utf-8")

        # save metadata
        output_metadata_file = DEFAULT_JSON_PATH / f"{html_file.stem}.json"
        output_metadata_file.parent.mkdir(parents=True, exist_ok=True)
        output_metadata_file.write_text(
            json.dumps(file_data, indent=2), encoding="utf-8"
        )
