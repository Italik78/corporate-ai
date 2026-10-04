import asyncio
import logging
import json
import os
from urllib.parse import quote, unquote, urljoin
import xml.etree.ElementTree as ET

import httpx

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("nextcloud-poller")

NEXTCLOUD_BASE_URL = os.environ["NEXTCLOUD_BASE_URL"].rstrip("/") + "/"
NEXTCLOUD_USERNAME = os.environ["NEXTCLOUD_USERNAME"]
NEXTCLOUD_PASSWORD = os.environ["NEXTCLOUD_PASSWORD"]
NEXTCLOUD_INCOMING_PATH = os.getenv(
    "NEXTCLOUD_INCOMING_PATH",
    "Corporate AI/Incoming/",
).strip("/") + "/"
INGESTION_URL = os.getenv(
    "INGESTION_URL",
    "http://corporate-ai-document-ingestion:8095",
).rstrip("/")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
STATE_FILE = os.getenv("STATE_FILE", "/tmp/nextcloud-poller-state.json")


def webdav_url(path: str) -> str:
    encoded = "/".join(quote(part, safe="") for part in path.strip("/").split("/"))
    return urljoin(NEXTCLOUD_BASE_URL, f"remote.php/dav/files/{NEXTCLOUD_USERNAME}/{encoded}/")


async def list_files(client: httpx.AsyncClient) -> list[dict]:
    url = webdav_url(NEXTCLOUD_INCOMING_PATH)

    response = await client.request(
        "PROPFIND",
        url,
        headers={
            "Depth": "1",
            "Content-Type": "application/xml",
        },
        content="""<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
    <d:prop>
        <oc:fileid/>
        <d:getetag/>
        <d:getcontentlength/>
        <d:getcontenttype/>
        <d:resourcetype/>
    </d:prop>
</d:propfind>""",
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"d": "DAV:"}
    files = []

    for item in root.findall("d:response", ns):
        href = item.findtext("d:href", default="", namespaces=ns)
        resource_type = item.find("d:propstat/d:prop/d:resourcetype/d:collection", ns)

        if not href or resource_type is not None:
            continue

        path = unquote(href)
        filename = path.rstrip("/").split("/")[-1]

        if not filename:
            continue

        files.append(
            {
                "filename": filename,
                "href": href,
                "file_id": int(
                    item.findtext(
                        "d:propstat/d:prop/oc:fileid",
                        default="0",
                        namespaces={"d": "DAV:", "oc": "http://owncloud.org/ns"},
                    )
                ),
                "etag": item.findtext(
                    "d:propstat/d:prop/d:getetag",
                    default="",
                    namespaces=ns,
                ).strip('"'),
                "size": int(
                    item.findtext(
                        "d:propstat/d:prop/d:getcontentlength",
                        default="0",
                        namespaces=ns,
                    )
                ),
            }
        )

    return files

async def write_back_metadata(
    client: httpx.AsyncClient,
    file_info: dict,
    result: dict,
) -> None:
    file_id = file_info["file_id"]
    status = result.get("status")
    ready = status == "READY"

    metadata = {
        "corporate_ai_status": "READY FOR RAG" if ready else str(status or "FAILED"),
        "corporate_ai_version": result.get("version", 0),
        "corporate_ai_pages": result.get("page_count") or 0,
        "corporate_ai_chunks": result.get("chunk_count", 0),
        "corporate_ai_indexed": result.get("indexed_count", 0),
        "corporate_ai_rag_ready": 1 if ready else 0,
    }

    url = (
        f"{NEXTCLOUD_BASE_URL.rstrip('/')}"
        f"/ocs/v1.php/apps/metavox/api/v1/files/{file_id}/metadata"
    )

    response = await client.post(
        url,
        headers={
            "OCS-APIRequest": "true",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"metadata": metadata},
    )
    response.raise_for_status()

    payload = response.json()
    if payload.get("ocs", {}).get("meta", {}).get("status") != "ok":
        raise RuntimeError(f"MetaVox write-back failed: {payload}")

    log.info(
        "MetaVox updated filename=%s file_id=%s status=%s version=%s pages=%s chunks=%s indexed=%s rag_ready=%s",
        file_info["filename"],
        file_id,
        metadata["corporate_ai_status"],
        metadata["corporate_ai_version"],
        metadata["corporate_ai_pages"],
        metadata["corporate_ai_chunks"],
        metadata["corporate_ai_indexed"],
        metadata["corporate_ai_rag_ready"],
    )


def load_state() -> dict:
    try:
        return json.loads(open(STATE_FILE, "r", encoding="utf-8").read())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    temporary = f"{STATE_FILE}.tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, STATE_FILE)
        directory_fd = os.open(os.path.dirname(STATE_FILE) or ".", os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def has_changed(state: dict, file_info: dict) -> bool:
    """Whether an ETag differs from the last successfully completed poll."""
    return state.get(file_info["href"]) != file_info["etag"]


async def ingest_file(client: httpx.AsyncClient, file_info: dict) -> None:
    href = file_info["href"]
    filename = file_info["filename"]

    if href.startswith("/"):
        url = urljoin(NEXTCLOUD_BASE_URL, href.lstrip("/"))
    else:
        url = urljoin(NEXTCLOUD_BASE_URL, href)

    log.info(
        "Downloading filename=%s size=%s etag=%s",
        filename,
        file_info["size"],
        file_info["etag"],
    )

    response = await client.get(url)
    response.raise_for_status()

    response_content = response.content

    ingest_response = await client.post(
        f"{INGESTION_URL}/v1/documents/ingest",
        files={
            "file": (
                filename,
                response_content,
                "application/octet-stream",
            )
        },
        data={
            "source_system": "nextcloud",
            "source_reference": f"{NEXTCLOUD_INCOMING_PATH}{filename}",
            "access_scope": "INTERNAL",
            "classification": "INTERNAL",
        },
    )
    if ingest_response.is_error:
        log.error(
            "Ingestion failed filename=%s status=%s detail=%s",
            filename,
            ingest_response.status_code,
            ingest_response.text,
        )
        ingest_response.raise_for_status()

    result = ingest_response.json()

    log.info(
        "Ingested filename=%s status=%s document_id=%s version=%s pages=%s chunks=%s indexed=%s warnings=%s",
        filename,
        result.get("status"),
        result.get("document_id"),
        result.get("version"),
        result.get("page_count"),
        result.get("chunk_count"),
        result.get("indexed_count"),
        result.get("warnings"),
    )

    await write_back_metadata(client, file_info, result)


async def run() -> None:
    timeout = httpx.Timeout(600.0)

    async with httpx.AsyncClient(
        auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD),
        timeout=timeout,
    ) as client:
        while True:
            try:
                files = await list_files(client)
                log.info("Found %d file(s) in %s", len(files), NEXTCLOUD_INCOMING_PATH)

                state = load_state()

                for file_info in files:
                    state_key = file_info["href"]
                    current_etag = file_info["etag"]

                    if not has_changed(state, file_info):
                        log.info(
                            "Skipping unchanged filename=%s etag=%s",
                            file_info["filename"],
                            current_etag,
                        )
                        continue

                    try:
                        await ingest_file(client, file_info)
                        state[state_key] = current_etag
                        save_state(state)
                    except Exception:
                        log.exception(
                            "Failed processing filename=%s",
                            file_info["filename"],
                        )

            except Exception:
                log.exception("Polling cycle failed")

            await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run())
