
"""
Database layer using Supabase for shared multi-user data.
Falls back to local JSON file for testing without Supabase.
"""
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Try to import supabase - fall back to local JSON if not available
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except Exception:
    SUPABASE_AVAILABLE = False


class LocalDB:
    """Local JSON file database for testing/development."""
    
    def __init__(self, db_path="audit_data.json"):
        self.db_path = Path(db_path)
        self.data = self._load()
    
    def _load(self):
        if self.db_path.exists():
            with open(self.db_path, 'r') as f:
                return json.load(f)
        return {"audits": {}, "claims": {}, "qr_map": {}}
    
    def _save(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get_audits(self, shift: str, audit_date: str) -> dict:
        """Get all audit records for a given shift and date."""
        key = f"{audit_date}_{shift}"
        return self.data["audits"].get(key, {})
    
    def save_audit(self, location: str, shift: str, audit_date: str, period: str,
                   status: str, container: str, mix: bool, pvm: bool, lbl: bool,
                   qr_issue: bool, auditor: str):
        """Save an audit record."""
        key = f"{audit_date}_{shift}"
        if key not in self.data["audits"]:
            self.data["audits"][key] = {}
        
        self.data["audits"][key][location] = {
            "status": status,
            "container": container,
            "mix": mix,
            "pvm": pvm,
            "lbl": lbl,
            "qr_issue": qr_issue,
            "period": period,
            "shift": shift,
            "audit_date": audit_date,
            "auditor": auditor,
            "timestamp": datetime.now().isoformat()
        }
        self._save()
        return True
    
    def claim_area(self, area: str, shift: str, audit_date: str, auditor: str) -> bool:
        """Claim an area for auditing. Returns True if successful."""
        key = f"{audit_date}_{shift}"
        if key not in self.data["claims"]:
            self.data["claims"][key] = {}
        
        # Check if already claimed by someone else
        existing = self.data["claims"][key].get(area)
        if existing and existing["auditor"] != auditor:
            # Check if claim is still active (within last 30 minutes)
            claim_time = datetime.fromisoformat(existing["timestamp"])
            elapsed = (datetime.now() - claim_time).total_seconds()
            if elapsed < 1800:  # 30 min
                return False
        
        self.data["claims"][key][area] = {
            "auditor": auditor,
            "timestamp": datetime.now().isoformat()
        }
        self._save()
        return True
    
    def release_area(self, area: str, shift: str, audit_date: str, auditor: str):
        """Release an area claim."""
        key = f"{audit_date}_{shift}"
        if key in self.data["claims"] and area in self.data["claims"][key]:
            if self.data["claims"][key][area]["auditor"] == auditor:
                del self.data["claims"][key][area]
                self._save()
    
    def get_claims(self, shift: str, audit_date: str) -> dict:
        """Get all current area claims."""
        key = f"{audit_date}_{shift}"
        claims = self.data["claims"].get(key, {})
        # Filter out expired claims (>30 min)
        active = {}
        for area, claim in claims.items():
            claim_time = datetime.fromisoformat(claim["timestamp"])
            elapsed = (datetime.now() - claim_time).total_seconds()
            if elapsed < 1800:
                active[area] = claim
        return active
    
    def flag_qr_issue(self, location: str, shift: str, audit_date: str, auditor: str):
        """Flag a QR issue for a location."""
        key = f"{audit_date}_{shift}"
        if key not in self.data["audits"]:
            self.data["audits"][key] = {}
        
        if location in self.data["audits"][key]:
            self.data["audits"][key][location]["qr_issue"] = True
            self.data["audits"][key][location]["timestamp"] = datetime.now().isoformat()
        else:
            self.data["audits"][key][location] = {
                "status": "",
                "container": "",
                "mix": False,
                "pvm": False,
                "lbl": False,
                "qr_issue": True,
                "period": "",
                "shift": shift,
                "audit_date": audit_date,
                "auditor": auditor,
                "timestamp": datetime.now().isoformat()
            }
        self._save()
    
    def get_history(self, date_from: str, date_to: str, shift_filter: str = None,
                    auditor_filter: str = None) -> list:
        """Get historical audit records for a date range."""
        results = []
        for key, locations in self.data["audits"].items():
            for location, record in locations.items():
                audit_date = record.get("audit_date", "")
                if not audit_date or audit_date < date_from or audit_date > date_to:
                    continue
                if shift_filter and shift_filter != "All":
                    if record.get("shift") != shift_filter:
                        continue
                if auditor_filter and auditor_filter != "All":
                    if record.get("auditor") != auditor_filter:
                        continue
                if not record.get("status"):
                    continue
                results.append({
                    "location": location,
                    "shift": record.get("shift", ""),
                    "audit_date": audit_date,
                    "period": record.get("period", ""),
                    "status": record.get("status", ""),
                    "container": record.get("container", ""),
                    "mix_match": record.get("mix", False),
                    "pvm": record.get("pvm", False),
                    "label_problem": record.get("lbl", False),
                    "qr_issue": record.get("qr_issue", False),
                    "auditor": record.get("auditor", ""),
                    "created_at": record.get("timestamp", "")
                })
        results.sort(key=lambda x: x.get("audit_date", ""), reverse=True)
        return results
    
    def get_auditors_list(self) -> list:
        """Get list of all auditors."""
        auditors = set()
        for key, locations in self.data["audits"].items():
            for location, record in locations.items():
                if record.get("auditor"):
                    auditors.add(record["auditor"])
        return sorted(list(auditors))


class SupabaseDB:
    """Supabase database for production multi-user sync."""
    
    def __init__(self):
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables required")
        self.client: Client = create_client(url, key)
    
    def get_audits(self, shift: str, audit_date: str) -> dict:
        """Get all audit records for a given shift and date."""
        response = self.client.table("audits").select("*").eq(
            "shift", shift).eq("audit_date", audit_date).execute()
        
        result = {}
        for row in response.data:
            result[row["location"]] = {
                "status": row["status"],
                "container": row.get("container", ""),
                "mix": row.get("mix_match", False),
                "pvm": row.get("pvm", False),
                "lbl": row.get("label_problem", False),
                "qr_issue": row.get("qr_issue", False),
                "period": row.get("period", ""),
                "shift": row["shift"],
                "audit_date": row["audit_date"],
                "auditor": row.get("auditor", ""),
                "timestamp": row.get("created_at", "")
            }
        return result
    
    def save_audit(self, location: str, shift: str, audit_date: str, period: str,
                   status: str, container: str, mix: bool, pvm: bool, lbl: bool,
                   qr_issue: bool, auditor: str):
        """Save an audit record (upsert)."""
        data = {
            "location": location,
            "shift": shift,
            "audit_date": audit_date,
            "period": period,
            "status": status,
            "container": container,
            "mix_match": mix,
            "pvm": pvm,
            "label_problem": lbl,
            "qr_issue": qr_issue,
            "auditor": auditor,
        }
        self.client.table("audits").upsert(
            data, on_conflict="location,shift,audit_date"
        ).execute()
        return True
    
    def claim_area(self, area: str, shift: str, audit_date: str, auditor: str) -> bool:
        """Claim an area. Returns True if successful."""
        # Check existing claim
        response = self.client.table("area_claims").select("*").eq(
            "area", area).eq("shift", shift).eq("audit_date", audit_date).execute()
        
        if response.data:
            existing = response.data[0]
            if existing["auditor"] != auditor:
                claim_time = datetime.fromisoformat(existing["created_at"].replace("Z", "+00:00"))
                elapsed = (datetime.now(claim_time.tzinfo) - claim_time).total_seconds()
                if elapsed < 1800:
                    return False
        
        # Upsert claim
        data = {
            "area": area,
            "shift": shift,
            "audit_date": audit_date,
            "auditor": auditor,
        }
        self.client.table("area_claims").upsert(
            data, on_conflict="area,shift,audit_date"
        ).execute()
        return True
    
    def release_area(self, area: str, shift: str, audit_date: str, auditor: str):
        """Release area claim."""
        self.client.table("area_claims").delete().eq(
            "area", area).eq("shift", shift).eq(
            "audit_date", audit_date).eq("auditor", auditor).execute()
    
    def get_claims(self, shift: str, audit_date: str) -> dict:
        """Get active claims."""
        response = self.client.table("area_claims").select("*").eq(
            "shift", shift).eq("audit_date", audit_date).execute()
        
        active = {}
        for row in response.data:
            claim_time = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            elapsed = (datetime.now(claim_time.tzinfo) - claim_time).total_seconds()
            if elapsed < 1800:
                active[row["area"]] = {
                    "auditor": row["auditor"],
                    "timestamp": row["created_at"]
                }
        return active
    
    def flag_qr_issue(self, location: str, shift: str, audit_date: str, auditor: str):
        """Flag QR issue."""
        self.save_audit(location, shift, audit_date, "", "", "", False, False, False, True, auditor)
    
    def get_history(self, date_from: str, date_to: str, shift_filter: str = None,
                    auditor_filter: str = None) -> list:
        """Get historical audit records for a date range."""
        query = self.client.table("audits").select("*").gte(
            "audit_date", date_from).lte("audit_date", date_to).neq("status", "")
        
        if shift_filter and shift_filter != "All":
            query = query.eq("shift", shift_filter)
        
        if auditor_filter and auditor_filter != "All":
            query = query.eq("auditor", auditor_filter)
        
        response = query.order("audit_date", desc=True).order("location").execute()
        return response.data
    
    def get_auditors_list(self) -> list:
        """Get list of all auditors who have submitted audits."""
        response = self.client.table("audits").select("auditor").execute()
        auditors = list(set(row["auditor"] for row in response.data if row.get("auditor")))
        auditors.sort()
        return auditors


def get_database():
    """Factory function to get the appropriate database instance."""
    if SUPABASE_AVAILABLE and os.environ.get("SUPABASE_URL"):
        try:
            return SupabaseDB()
        except Exception:
            pass
    return LocalDB()

