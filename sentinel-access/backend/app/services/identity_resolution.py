import re


def stable_identity_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"id-{slug or 'identity'}"


def initials_for(name: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", name) if part]
    return "".join(part[0].upper() for part in parts[:2]) or "ID"


def resolve_identity_id(record: dict) -> str | None:
    """Prefer an explicit stable identityId; only fall back to deriving one
    from a display/principal name when no ID was supplied (identity
    directory imports). Never used for event ingestion, which must cite an
    already-known identityId rather than guess one from a name."""
    explicit = record.get("identityId") or record.get("id")
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    name = record.get("name") or record.get("principalName") or record.get("displayName")
    if name and str(name).strip():
        return stable_identity_id(str(name))
    return None

