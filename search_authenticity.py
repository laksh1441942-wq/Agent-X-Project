# from typing import Any
# import httpx

# OPENALEX_URL = "https://api.openalex.org/works"


# async def fetch_openalex_papers(
#     query: str,
#     client: httpx.AsyncClient,
#     max_papers: int = 5,
# ) -> tuple[list[dict[str, Any]], list[str]]:
#     """
#     Search OpenAlex for research papers matching a query.

#     Returns:
#         papers: List of paper metadata dictionaries.
#         warnings: List of errors or warning messages.
#     """
#     papers = []
#     warnings = []

#     params = {
#         "search": query,
#         "per-page": max_papers,
#     }

#     try:
#         response = await client.get(
#             OPENALEX_URL,
#             params=params,
#         )
#         response.raise_for_status()
#         data = response.json()

#         for item in data.get("results", []):
#             doi = item.get("doi")

#             papers.append({
#                 "title": item.get("title"),
#                 "publication_year": item.get("publication_year"),
#                 "doi": doi,
#                 "openalex_id": item.get("id"),
#                 "authors": [
#                     author.get("author", {}).get("display_name")
#                     for author in item.get("authorships", [])
#                 ],
#             })

#     except httpx.HTTPError as error:
#         warnings.append(f"OpenAlex request failed: {error}")

#     except (ValueError, TypeError) as error:
#         warnings.append(f"Could not parse OpenAlex response: {error}")

#     return papers, warnings






from typing import Any

import httpx

OPENALEX_URL = "https://api.openalex.org/works"
CROSSREF_URL = "https://api.crossref.org/works"


async def fetch_openalex_papers(
    query: str,
    client: httpx.AsyncClient,
    max_papers: int = 5,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Search OpenAlex for research papers."""

    papers: list[dict[str, Any]] = []
    warnings: list[str] = []

    params = {
        "search": query,
        "per-page": max_papers,
    }

    try:
        response = await client.get(OPENALEX_URL, params=params)
        response.raise_for_status()

        data = response.json()

        for item in data.get("results", []):
            papers.append({
                "title": item.get("title"),
                "publication_year": item.get("publication_year"),
                "doi": item.get("doi"),
                "openalex_id": item.get("id"),
                "authors": [
                    author.get("author", {}).get("display_name")
                    for author in item.get("authorships", [])
                ],
            })

    except httpx.HTTPError as error:
        warnings.append(f"OpenAlex request failed: {error}")

    except (ValueError, TypeError) as error:
        warnings.append(f"Could not parse OpenAlex response: {error}")

    return papers, warnings


async def fetch_crossref_metadata(
    doi: str,
    client: httpx.AsyncClient,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Fetch paper metadata from Crossref using its DOI."""

    warnings: list[str] = []

    if not doi or not doi.strip():
        warnings.append("DOI is empty.")
        return None, warnings

    doi = doi.strip()

    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
    ):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break

    url = f"{CROSSREF_URL}/{doi}"

    try:
        response = await client.get(
            url,
            headers={"User-Agent": "ResearchPilot/1.0"},
        )

        if response.status_code == 404:
            warnings.append(f"DOI not found in Crossref: {doi}")
            return None, warnings

        response.raise_for_status()

        item = response.json().get("message", {})

        published = (
            item.get("published-print")
            or item.get("published-online")
            or item.get("created")
            or {}
        )

        date_parts = published.get("date-parts", [[]])

        year = (
            date_parts[0][0]
            if date_parts and date_parts[0]
            else None
        )

        metadata = {
            "title": item.get("title", []),
            "DOI": item.get("DOI"),
            "author": item.get("author", []),
            "publisher": item.get("publisher"),
            "type": item.get("type"),
            "URL": item.get("URL"),
            "publication_year": year,
        }

        return metadata, warnings

    except httpx.HTTPError as error:
        warnings.append(f"Crossref request failed: {error}")
        return None, warnings

    except (ValueError, TypeError) as error:
        warnings.append(f"Could not parse Crossref response: {error}")
        return None, warnings