import requests
from typing import Dict, Any, Optional
from backend.utils.npi import is_valid_npi

NPI_API_URL = "https://npiregistry.cms.hhs.gov/api/"
TIMEOUT = 5


def _pick_primary_address(addresses: list) -> Optional[dict]:
    if not addresses:
        return None

    for addr in addresses:
        if addr.get("address_purpose") in ("LOCATION", "PRIMARY"):
            return addr

    return addresses[0]


def _pick_primary_taxonomy(taxonomies: list) -> Optional[dict]:
    if not taxonomies:
        return None

    for tax in taxonomies:
        if tax.get("primary") is True:
            return tax

    return taxonomies[0]


def fetch_npi_data(npi_number: str) -> Dict[str, Any]:
    """
    Fetch provider data from CMS NPI Registry API v2.1
    """
    if not is_valid_npi(npi_number):
        return {}
    params = {
        "number": npi_number,
        "version": "2.1",
        "limit": 1,
    }

    try:
        resp = requests.get(NPI_API_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return {}

    results = payload.get("results", [])
    if not results:
        return {}

    provider = results[0]

    # Address
    addr = _pick_primary_address(provider.get("addresses", []))
    phone = addr.get("telephone_number") if addr else None

    address = None
    if addr:
        parts = [
            addr.get("address_1"),
            addr.get("city"),
            addr.get("state"),
            addr.get("postal_code"),
        ]
        address = ", ".join(p for p in parts if p)

    # Taxonomy
    taxonomy = _pick_primary_taxonomy(provider.get("taxonomies", []))
    specialty = taxonomy.get("desc") if taxonomy else None
    license_no = taxonomy.get("license") if taxonomy else None

    return {
        "phone": phone,
        "address": address,
        "specialty": specialty,
        "license_no": license_no,
        # IMPORTANT: NPI DOES NOT PROVIDE LICENSE EXPIRY
        "license_expiry": None,
    }
