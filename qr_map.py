
"""
QR UUID → STG Location mapping for ROC1.
Loads the ROC1_qr_map.csv and provides lookup functions.
Supports learning new UUIDs at runtime.
"""
import csv
import os
from pathlib import Path

# Path to the CSV file (changed from DAB2 to ROC1)
QR_MAP_FILE = Path(__file__).parent / "ROC1_qr_map.csv"


def load_qr_map() -> dict:
    """Load QR UUID → STG_Location mapping from CSV."""
    qr_map = {}
    if QR_MAP_FILE.exists():
        with open(QR_MAP_FILE, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uuid = row['QR_UUID'].strip().upper()
                stg = row['STG_Location'].strip().upper()
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
    - source: 'direct' if typed STG-ID, 'qr_map' if UUID resolved, 'unknown' if UUID not found
    """
    scan = scan_input.strip().upper()

    # Check if it's already a valid STG-ID format
    if scan.startswith('STG-'):
        return scan, 'direct'

    # Try to resolve as UUID
    if scan in qr_map:
        return qr_map[scan], 'qr_map'

    # Unknown UUID
    return scan, 'unknown'


def learn_uuid(uuid: str, stg_location: str, qr_map: dict) -> dict:
    """
    Learn a new UUID → STG mapping and save to CSV.
    Returns updated qr_map.
    """
    uuid = uuid.strip().upper()
    stg_location = stg_location.strip().upper()
    qr_map[uuid] = stg_location
    save_qr_map(qr_map)
    return qr_map

