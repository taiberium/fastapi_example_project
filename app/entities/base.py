from sqlmodel import SQLModel

# SQLModel is the shared declarative base + metadata for all table models.
# Kept behind the `Base` name so alembic/tests have one import site for the metadata.
Base = SQLModel
