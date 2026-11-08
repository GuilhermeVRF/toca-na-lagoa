"""Database engine, session helpers and initial seed."""

from collections.abc import Iterator

from sqlalchemy import Connection, Engine, MetaData, Table, UniqueConstraint, inspect, literal, text
from sqlmodel import Session, SQLModel, create_engine

from app.config import DATA_DIR, DATABASE_URL
from app.models import Settings

engine: Engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    """Create tables and seed default settings on first run."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _add_missing_columns()
    _delete_sale_rows()
    _rebuild_tables_with_changed_keys()
    _drop_removed_columns()
    with Session(engine) as session:
        if session.get(Settings, 1) is None:
            session.add(Settings(id=1))
            session.commit()


def _add_missing_columns() -> None:
    """Add model columns created after the database was (``create_all`` never alters tables).

    Existing rows get the column's scalar default from the model, or NULL when it has none.
    """
    with engine.begin() as connection:
        for table in SQLModel.metadata.sorted_tables:
            existing = {column["name"] for column in inspect(connection).get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    column_type = column.type.compile(dialect=connection.dialect)
                    default = _default_clause(connection, column.default)
                    connection.execute(
                        text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column_type}{default}'),
                    )


def _default_clause(connection: Connection, default) -> str:
    """SQL ``DEFAULT`` clause for a column default, empty when there is no scalar default."""
    if default is None or not default.is_scalar or default.arg is None:
        return ""
    value = literal(default.arg).compile(dialect=connection.dialect, compile_kwargs={"literal_binds": True})
    return f" DEFAULT {value}"


def _delete_sale_rows() -> None:
    """Delete the rows stored by the search of listings for sale, which was removed.

    Rentals and sales were keyed by ``business``; once only rentals are left the
    tables can go back to their old keys without two rows colliding.
    """
    with engine.begin() as connection:
        if "business" in _stored_columns(connection, "listing"):
            connection.execute(
                text(
                    "DELETE FROM pricehistory WHERE listing_id IN (SELECT id FROM listing WHERE business != 'rent')",
                ),
            )
            connection.execute(text("DELETE FROM listing WHERE business != 'rent'"))
        if "business" in _stored_columns(connection, "sourcestatus"):
            connection.execute(text("DELETE FROM sourcestatus WHERE business != 'rent'"))


def _stored_columns(connection: Connection, table_name: str) -> set[str]:
    """Column names of a table as stored in the database."""
    return {column["name"] for column in inspect(connection).get_columns(table_name)}


def _rebuild_tables_with_changed_keys() -> None:
    """Rebuild tables whose primary key or unique constraints changed in the model.

    SQLite cannot alter constraints, so the table is recreated and its rows are
    copied over, following the procedure in the SQLite docs. Runs after
    ``_add_missing_columns``, so every model column already exists.
    """
    with engine.begin() as connection:
        for table in SQLModel.metadata.sorted_tables:
            if _stored_keys(connection, table.name) != _model_keys(table):
                _rebuild_table(connection, table)


def _stored_keys(connection: Connection, table_name: str) -> tuple:
    """Primary key and unique constraints of a table as stored in the database."""
    inspector = inspect(connection)
    primary_key = tuple(sorted(inspector.get_pk_constraint(table_name)["constrained_columns"]))
    uniques = sorted(tuple(sorted(unique["column_names"])) for unique in inspector.get_unique_constraints(table_name))
    return primary_key, uniques


def _model_keys(table: Table) -> tuple:
    """Primary key and unique constraints of a table as declared in the models."""
    primary_key = tuple(sorted(column.name for column in table.primary_key.columns))
    uniques = sorted(
        tuple(sorted(column.name for column in constraint.columns))
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    )
    return primary_key, uniques


def _rebuild_table(connection: Connection, table: Table) -> None:
    """Recreate a table from the model, keeping its rows and ids."""
    staging = table.to_metadata(MetaData(), name=f"{table.name}_rebuild")
    staging.indexes.clear()
    staging.create(connection)
    columns = ", ".join(f'"{column.name}"' for column in table.columns)
    connection.execute(text(f'INSERT INTO "{staging.name}" ({columns}) SELECT {columns} FROM "{table.name}"'))
    connection.execute(text(f'DROP TABLE "{table.name}"'))
    connection.execute(text(f'ALTER TABLE "{staging.name}" RENAME TO "{table.name}"'))
    for index in table.indexes:
        index.create(connection)


def _drop_removed_columns() -> None:
    """Drop stored columns the models no longer declare.

    Runs after ``_rebuild_tables_with_changed_keys``, which already drops the
    columns of the tables it recreates, including indexed ones that SQLite
    could not drop here.
    """
    with engine.begin() as connection:
        for table in SQLModel.metadata.sorted_tables:
            for name in sorted(_stored_columns(connection, table.name) - set(table.columns.keys())):
                connection.execute(text(f'ALTER TABLE "{table.name}" DROP COLUMN "{name}"'))


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    with Session(engine) as session:
        yield session


def load_settings(session: Session) -> Settings:
    """Return the single settings row."""
    settings = session.get(Settings, 1)
    if settings is None:
        raise RuntimeError("settings row missing; init_db() was not called")
    return settings
