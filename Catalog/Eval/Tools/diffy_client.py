import os
import json
import logging
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)

class DiffyApiClient:
    """
    A client for interacting with a live Diffy service.
    This class is responsible for making HTTP requests to the Diffy API.
    """
    def __init__(self, base_url: str, api_key: str):
        logger.info(f"Initializing DiffyApiClient with base_url: {base_url}")
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "X-Diffy-API-Key": api_key,
        }
        self.timeout = 30.0

    async def get_diff_report(self, diff_id: int) -> Dict[str, Any]:
        """
        Fetches a specific diff report by its ID from the live Diffy service.
        """
        endpoint = f"/api/diffs/{diff_id}" # Corrected endpoint path
        request_url = f"{self.base_url}{endpoint}"
        logger.info(f"Making live API call to GET {request_url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    request_url, headers=self.headers, timeout=self.timeout
                )
                response.raise_for_status()
                report = response.json()
                logger.info(f"Successfully fetched report for ID: {diff_id}")
                return report
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on GET {request_url}: {e.response.status_code} - {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Network error on GET {request_url}: {e}")
                raise

    async def create_project_if_not_exists(self, slug: str, name: str):
        """
        Creates a new project in Diffy, ignoring errors if it already exists.
        """
        endpoint = "/api/projects"
        request_url = f"{self.base_url}{endpoint}"
        payload = {"slug": slug, "name": name}
        logger.info(f"Ensuring project '{slug}' exists by POSTing to {request_url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(request_url, headers=self.headers, json=payload, timeout=self.timeout)
                # If the project already exists, Diffy returns a 409 Conflict, which we can safely ignore.
                if response.status_code == 409:
                    logger.info(f"Project '{slug}' already exists. Continuing.")
                    return
                response.raise_for_status()
                logger.info(f"Successfully created or confirmed project '{slug}'.")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:
                    logger.info(f"Project '{slug}' already exists. Continuing.")
                else:
                    logger.error(f"HTTP error creating project {slug}: {e.response.status_code} - {e.response.text}")
                    raise
            except httpx.RequestError as e:
                logger.error(f"Network error creating project {slug}: {e}")
                raise

    async def create_diff(self, baseline: str, shadow: str, project: str) -> Dict[str, Any]:
        """
        Creates a new diff on the Diffy server by sending raw HTTP requests.
        """
        endpoint = f"/api/{project}/diffs" # Corrected endpoint path
        request_url = f"{self.base_url}{endpoint}"
        logger.info(f"Making live API call to POST {request_url}")

        # The payload for Diffy is the raw text of the HTTP requests
        payload = {
            "candidate": shadow,
            "primary": baseline,
            "secondary": baseline, # In many setups, secondary is the same as primary
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    request_url, headers=self.headers, data=json.dumps(payload), timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
                diff_id = result.get("id")
                if not diff_id:
                    logger.error(f"Diffy API did not return an 'id' in the response. Full response: {result}")
                    raise ValueError("Diffy API did not return a valid diff ID.")
                
                logger.info(f"Successfully created new diff with ID: {diff_id}")
                return result
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on POST {request_url}: {e.response.status_code} - {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Network error on POST {request_url}: {e}")
                raise
