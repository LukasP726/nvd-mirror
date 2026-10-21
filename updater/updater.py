import gzip
import hashlib
import logging
import os
import re
import tempfile
import time

from pathlib import Path

import requests


BASE_URL = "https://nvd.nist.gov/feeds/json/cve/2.0"
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "21600"))
REQUEST_TIMEOUT = (10, 300)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

LOG = logging.getLogger("nvd-updater")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "nvd-mirror/0.1",
})

META_PATTERN = re.compile(
    r"^lastModifiedDate:(?P<modified>.+)\r?\n"
    r"size:(?P<size>\d+)\r?\n"
    r"zipSize:(?P<zip_size>\d+)\r?\n"
    r"gzSize:(?P<gz_size>\d+)\r?\n"
    r"sha256:(?P<sha256>[0-9a-fA-F]{64})\s*$"
)


def get_metadata(name: str) -> dict:
    """Stáhne a ověří metadata jednoho feedu."""
    url = f"{BASE_URL}/nvdcve-2.0-{name}.meta"

    response = SESSION.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    match = META_PATTERN.fullmatch(response.text.strip())

    #body = response.text.strip()
    #match = META_PATTERN.fullmatch(body)
    

    if not match:
        raise ValueError(f"Neplatná metadata feedu {name}")

    metadata = match.groupdict()

    metadata["size"] = int(metadata["size"])
    metadata["gz_size"] = int(metadata["gz_size"])
    metadata["zip_size"] = int(metadata["zip_size"])
    metadata["sha256"] = metadata["sha256"].lower()

    return metadata


def update_feed(name: str) -> bool:
    """
    Aktualizuje jeden GZIP feed.

    Vrací True, pokud byl feed aktualizován.
    """
    metadata = get_metadata(name)

    filename = f"nvdcve-2.0-{name}.json.gz"
    target = DATA_DIR / filename
    target_meta = DATA_DIR / f"nvdcve-2.0-{name}.meta"

    # Pokud máme stejnou verzi a její integrita je ověřena,
    # není nutné feed znovu stahovat.
    if target.exists() and target_meta.exists():
        try:
            local_meta = get_local_metadata(target_meta)

            if (
                local_meta.get("sha256") == metadata["sha256"]
                and verify_gzip(target, metadata)
            ):
                LOG.info("%s: beze změny", name)
                return False

        except (OSError, ValueError, EOFError, gzip.BadGzipFile):
            LOG.warning("%s: lokální kopie není validní", name)

    url = f"{BASE_URL}/{filename}"

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{filename}.",
        suffix=".tmp",
        dir=DATA_DIR,
    )
    os.close(fd)

    temporary_path = Path(temporary_name)

    try:
        LOG.info("%s: stahuji feed", name)

        with SESSION.get(
            url,
            stream=True,
            timeout=REQUEST_TIMEOUT,
        ) as response:
            response.raise_for_status()

            with temporary_path.open("wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        output.write(chunk)

        # Ověření velikosti komprimovaného souboru.
        if temporary_path.stat().st_size != metadata["gz_size"]:
            raise ValueError(
                f"{name}: nesouhlasí velikost GZIP souboru"
            )

        # Ověření SHA-256 a velikosti nekomprimovaného JSON.
        if not verify_gzip(temporary_path, metadata):
            raise ValueError(
                f"{name}: neodpovídá SHA-256 nebo velikost JSON"
            )

        # Zveřejnění nového feedu atomickým přejmenováním.
        os.replace(temporary_path, target)

        # Metadata ukládáme až po úspěšném ověření feedu.
        meta_tmp = target_meta.with_suffix(".meta.tmp")
        meta_tmp.write_text(
            "\n".join([
                f"lastModifiedDate:{metadata['modified']}",
                f"size:{metadata['size']}",
                f"zipSize:{metadata['zip_size']}",
                f"gzSize:{metadata['gz_size']}",
                f"sha256:{metadata['sha256']}",
            ]) + "\n",
            encoding="utf-8",
        )
        os.replace(meta_tmp, target_meta)

        LOG.info("%s: aktualizace dokončena", name)
        return True

    finally:
        temporary_path.unlink(missing_ok=True)


def verify_gzip(path: Path, metadata: dict) -> bool:
    """Ověří dekomprimovaný obsah proti metadatům NVD."""
    digest = hashlib.sha256()
    uncompressed_size = 0

    with gzip.open(path, "rb") as source:
        while True:
            chunk = source.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)
            uncompressed_size += len(chunk)

    return (
        uncompressed_size == metadata["size"]
        and digest.hexdigest() == metadata["sha256"]
    )


def get_local_metadata(path: Path) -> dict:
    """Načte lokálně uložená metadata."""
    text = path.read_text(encoding="utf-8").strip()
    match = META_PATTERN.fullmatch(text)

    if not match:
        raise ValueError("Neplatná lokální metadata")

    result = match.groupdict()
    result["sha256"] = result["sha256"].lower()

    return result


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    selected_feed = os.getenv("NVD_FEED", "all").strip().lower()

    current_year = time.gmtime().tm_year
    feeds = [
        *(str(year) for year in range(2002, current_year + 1)),
        "modified",
    ]

    if selected_feed == "all": 
        feeds = all_feeds 
    elif selected_feed == "years": 
        feeds = [feed for feed in all_feeds if feed.isdigit()] 
    elif selected_feed == "modified": 
        feeds = ["modified"] 
    elif selected_feed.isdigit() and selected_feed in all_feeds: 
        feeds = [selected_feed] 
    else: 
        raise ValueError(f"Neplatný výběr feedu: {selected_feed!r}") 
    LOG.info("Vybrané feedy: %s", ", ".join(feeds))

    while True:
        LOG.info("Začíná kontrola NVD feedů")

        for feed in feeds:
            try:
                update_feed(feed)
            except Exception:
                LOG.exception("Aktualizace feedu %s selhala", feed)

        LOG.info(
            "Kontrola dokončena; další kontrola za %s sekund",
            UPDATE_INTERVAL,
        )

        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()