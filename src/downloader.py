"""
WHDownloader class to handle efficiently retrieving pages from whitehouse.gov
"""

# future imports
from __future__ import annotations

# imports
import json
import hashlib
import urllib.parse
from pathlib import Path
from typing import AsyncIterator

# packages
import lxml.html
import httpx


# constants
from config import (
    DEFAULT_HASH_PATH,
    DEFAULT_SLEEP,
    TIMEOUT_CONFIG,
    BASE_URL,
    PRESIDENTIAL_ACTION_PATH,
    EXCLUDE_EXTENSIONS,
    DEFAULT_RAW_PATH,
)


class WHDownloader:
    """
    Class to handle efficiently retrieving pages from whitehouse.gov
    """

    @staticmethod
    def load_hashes(hash_path: Path = DEFAULT_HASH_PATH) -> dict:
        """
        Load the hash file from disk.

        Args:
            hash_path (str): path to the hash file

        Returns:
            dict: hash file contents
        """
        # check if file exists
        if not hash_path.exists():
            return {}

        # read file
        with open(hash_path, "rt", encoding="utf-8") as hash_file:
            return json.load(hash_file)

    @staticmethod
    def save_hashes(hashes: dict, hash_path: Path = DEFAULT_HASH_PATH) -> None:
        """
        Save the hash file to disk.

        Args:
            hashes (dict): hash file contents
            hash_path (str): path to the hash file

        Returns:
            None
        """
        # write file
        with open(hash_path, "wt", encoding="utf-8") as hash_file:
            hash_file.write(json.dumps(hashes, indent=2))

    def __init__(self, overwrite: bool = False):
        """
        Initialize http2 client and cache for downloaded pages.

        Args:
            overwrite (bool): overwrite existing files

        Returns:
            None
        """
        # set overwrite flag
        self.overwrite = overwrite

        # init client
        self.client = httpx.AsyncClient(
            http2=True,
            follow_redirects=True,
            timeout=TIMEOUT_CONFIG,
            headers={"User-Agent": "wh-pa (https://github.com/mjbommar/wh-pa)"},
        )

        # load hashes
        self.hashes = WHDownloader.load_hashes()

        # check seen paths in this session
        self.seen_paths = set()

    async def __aenter__(self) -> WHDownloader:
        """
        Return client when entering.

        Args:
            None

        Returns:
            WHDownloader: client
        """
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """
        Clean up client when exiting.

        Args:
            None

        Returns:
            None
        """
        # close client
        try:
            await self.client.aclose()
        except Exception:
            pass

        # save hashes
        try:
            WHDownloader.save_hashes(self.hashes)
        except Exception:
            pass

    def get_path(self, path: str) -> str:
        """
        Get the full URL for a given path.

        Args:
            path (str): path to the page

        Returns:
            str: full URL
        """
        # join the base URL and path
        full_url = urllib.parse.urljoin(BASE_URL.rstrip("/"), path.strip())
        return full_url

    @staticmethod
    def save_path(path: str, content: bytes) -> Path:
        """
        Save the content to disk.

        Args:
            path (str): path to the page
            content (bytes): content to save

        Returns:
            Path: path to the saved file
        """
        # set up suffix and output path
        hash_suffix = hashlib.blake2b(content, digest_size=4).hexdigest()  # type: ignore

        try:
            output_file_name = Path(
                path.replace("https://", "").lstrip("/")
            ).with_suffix("." + hash_suffix)
        except ValueError:
            # handle index/root pages
            output_file_name = Path("index").with_suffix("." + hash_suffix)

        # set output file path
        output_file_path = DEFAULT_RAW_PATH / output_file_name
        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        # write the file
        with open(output_file_path, "wb") as output_file:
            output_file.write(content)

        return output_file_path

    # wrap client get to update hashes
    async def get(self, path: str) -> tuple[bytes, int, dict, bool]:
        """
        Get the page at the given path.

        Args:
            path (str): path to the page

        Returns:
            tuple[bytes, int, dict, bool]: response content, status code, headers, and change status
        """
        # fetch the page
        try:
            response = await self.client.get(self.get_path(path))
        except Exception:
            return b"", 0, {}, False

        # get the content bytes
        content = response.content

        # update the hash
        if path not in self.hashes:
            changed = True
            self.hashes[path] = hashlib.blake2b(content).hexdigest()
        else:
            changed = self.hashes[path] != hashlib.blake2b(content).hexdigest()
            self.hashes[path] = hashlib.blake2b(content).hexdigest()  # type: ignore

        # save the path
        self.save_path(path, content)

        return response.content, response.status_code, response.headers, changed

    async def update_path(self, path: str) -> AsyncIterator[Path, None]:
        """
        Update the archive of whitehouse.gov presidential actions.

        Args:
            path (str): path to the page to download

        Returns:
            AsyncGenerator[Path, None]: path to the downloaded pages
        """
        # fetch the page
        content, http_code, headers, changed = await self.get(path)

        # add to seen
        self.seen_paths.add(path)

        if changed or self.overwrite:
            # parse out any embedded links
            try:
                path_page = lxml.html.fromstring(content)
                for link in path_page.xpath("//a/@href"):
                    try:
                        parsed_link = urllib.parse.urlparse(link)
                    except Exception as e:
                        print("exception", path, e)
                        continue

                    # check if domain matches whitehouse.gov
                    if (
                        parsed_link.netloc is not None
                        and parsed_link.netloc != "www.whitehouse.gov"
                    ):
                        continue

                    # check for empty path
                    if parsed_link.path.strip() == "":
                        continue

                    # check if we've seen it
                    if parsed_link.path in self.seen_paths:
                        continue

                    # check if any of the extensions are excluded
                    if any(
                        link.lower().endswith(ext.lower()) for ext in EXCLUDE_EXTENSIONS
                    ):
                        continue

                    # yield the path
                    print(parsed_link.path)
                    async for link_path in self.update_path(parsed_link.path):
                        yield link_path
            except Exception as e:
                print("exception", path, e)


async def amain():
    # set up downloader
    async with WHDownloader(overwrite=True) as downloader:
        # update the path
        async for path in downloader.update_path(PRESIDENTIAL_ACTION_PATH):
            await asyncio.sleep(DEFAULT_SLEEP)


if __name__ == "__main__":
    import asyncio

    asyncio.run(amain())
