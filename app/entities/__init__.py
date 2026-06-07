"""entities — SQLAlchemy ORM models, the shared domain objects.

These map directly to database tables and are the only objects that flow through
service and repository. Top-level (not inside persistence/) because both the
service and the repository layers depend on them. No Pydantic/DTOs and no
business logic here.
"""
