"""
Fixtures for unit tests.
"""
#standard imports

# third party imports
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# project imports
from hashtheplanet.sql.db_connector import Base

@pytest.fixture(name="engine", scope="session")
def fixture_engine():
    """
    Returns an engine, stored in memory.
    """
    return create_engine("sqlite://")


@pytest.fixture(name="tables", scope="session")
def fixture_tables(engine):
    """
    Creates tables, and drop them after the test.
    """
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(name="dbsession")
def fixture_dbsession(engine, tables): # pylint: disable=unused-argument
    """
    Returns an sqlalchemy session, and after the test tears down everything properly.
    """
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    # use the connection with the already started transaction
    session = Session(bind=connection)

    yield session

    session.close()
    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()
