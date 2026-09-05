
"""
QR UUID → STG Location mapping for ROC1.
Loads the ROC1_qr_map.csv and provides lookup functions.
Supports learning new UUIDs at runtime.
"""
import csv
import os
from pathlib import Path

# Path to the CSV file
QR_MAP_FILE = Path(__file__).parent / "ROC1_qr_map.csv"


def load_qr_map() -> dict:
    """Load QR UUID → STG_Location mapping from CSV."""
    qr_map = {}
    if QR_MAP_FILE.exists():
        with open(QR_MAP_FILE, 'r', newline='') as f:
            reader = csv.DictReader(f)
            # Normalize headers to handle any case/naming variation
            headers = reader.fieldnames or []
            # Find the STG location column
            stg_col = None
            uuid_col = None
            for h in headers:
                h_upper = h.strip().upper()
                if 'STG' in h_upper or 'LOCATION' in h_upper:
                    stg_col = h
                if 'UUID' in h_upper or 'QR' in h_upper:
                    uuid_col = h
            # Fallback: use first and second columns
            if not stg_col and len(headers) >= 1:
                stg_col = headers[0]
            if not uuid_col and len(headers) >= 2:
                uuid_col = headers[1]

            if stg_col and uuid_col:
                for row in reader:
                    stg = (row.get(stg_col) or '').strip().upper()
                    uuid = (row.get(uuid_col) or '').strip().upper()
                    if uuid and stg:
                        qr_map[uuid] = stg
    return qr_map


def save_qr_map(qr_map: dict):
    """Save the full QR map back to CSV."""
    with open(QR_MAP_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['STG_Location', 'QR_UUID'])
        for uuid, stg in sorted(qr_map.items(), key=lambda x: x[1]):
            writer.writerow([stg, uuid])


def resolve_scan(scan_input: str, qr_map: dict) -> tuple:
    """
    Resolve a scan input to a STG location.

    Returns: (stg_id, source)
    - source: 'direct' if typed STG-ID, 'qr_map' if UUID resolved, 'unknown' if not found
    """
    scan = scan_input.strip().upper()

    # Check if it's already a valid STG-ID format
    if scan.startswith('STG-'):
        return scan, 'direct'

    # Try to resolve as UUID
    if scan in qr_map:
        return qr_map[scan], 'qr_map'

    # Unknown UUID
    return None, 'unknown'


def learn_uuid(uuid: str, stg_id: str, qr_map: dict) -> dict:
    """Add a new UUID → STG mapping and persist it."""
    uuid = uuid.strip().upper()
    stg_id = stg_id.strip().upper()
    qr_map[uuid] = stg_id
    save_qr_map(qr_map)
    return qr_map


def get_location_from_uuid(uuid: str, qr_map: dict = None) -> str:
    """Get STG location from UUID. Loads map if not provided."""
    if qr_map is None:
        qr_map = load_qr_map()
    result = qr_map.get(uuid.strip().upper())
    if result:
        return result
    return None

