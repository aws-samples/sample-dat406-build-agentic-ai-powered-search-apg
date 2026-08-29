"""Participant-facing identity for the configured PostgreSQL data source."""


def database_source_label() -> str:
    """Name the database actually configured for this process.

    Local development runs the Aurora-compatible schema on PostgreSQL. A deployed
    Aurora cluster endpoint is identifiable by the RDS cluster hostname; any other
    remote PostgreSQL host stays generic rather than being promoted to Aurora by
    assumption.
    """
    from config import settings

    host = str(settings.DB_HOST or "").strip().lower()
    if host in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}:
        return "Local PostgreSQL"
    if ".rds.amazonaws.com" in host and (
        ".cluster-" in host or ".cluster-ro-" in host
    ):
        return "Aurora PostgreSQL"
    return "PostgreSQL"
