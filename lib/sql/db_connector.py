"""
This module handles connections and requests to the database
"""
# standard imports
from json import JSONEncoder, loads

# third party imports
from loguru import logger
from sqlalchemy import Column, Text, JSON
from sqlalchemy import select, update
from sqlalchemy.ext.declarative import declarative_base, declared_attr

# project imports


Base = declarative_base()

class Tag(Base):
    """
    This class is a model for tag table
    """
    @declared_attr
    def __tablename__(cls): # pylint: disable=no-self-argument
        return cls.__name__.lower()

    technology = Column(Text, nullable=False, primary_key=True)
    tag = Column(Text, nullable=False, primary_key=True)

    def __repr__(self):
        return f"Tag (technology={self.technology}, tag={self.tag})"

class File(Base):
    """
    This class is a model for file table
    """
    @declared_attr
    def __tablename__(cls): # pylint: disable=no-self-argument
        return cls.__name__.lower()

    technology = Column(Text, nullable=False, primary_key=True)
    path = Column(Text, nullable=False, primary_key=True)

    def __repr__(self):
        return f"File (technology={self.technology}, path={self.path})"

class Hash(Base):
    """
    This class is a model for hash table
    """
    @declared_attr
    def __tablename__(cls): # pylint: disable=no-self-argument
        return cls.__name__.lower()

    hash = Column(Text, nullable=False, primary_key=True)
    technology = Column(Text, nullable=False)
    versions = Column(JSON, nullable=False)

    def __repr__(self):
        return f"Hash (hash={self.hash}, technology={self.technology}, versions={self.versions})"

class DbConnector():
    """
    This class implements method to connect to and request the database.
    """
    @staticmethod
    def insert_tag(session, technology, tag):
        """
        Insert a new tag related to technology in tag table if it does not exist yet.
        """
        stmt = select(Tag).filter_by(technology=technology, tag=str(tag))
        entry = session.execute(stmt).scalar_one_or_none()

        if not entry:
            new_tag = Tag(technology=technology, tag=str(tag))
            session.add(new_tag)
            logger.info(f"Entry {new_tag} added to tag database")
        else:
            logger.debug(f"Entry {entry} already exists in tags database")

    def insert_tags(self, session, technology, tags):
        """
        Insert a list of tags related to technology.
        """
        for _, tag in enumerate(tags):
            self.insert_tag(session, technology, tag)

    @staticmethod
    def get_tags(session, technology):
        """
        Returns all the tags related to technology.
        """
        stmt = select(Tag).filter_by(technology=technology)
        tags = session.execute(stmt).scalars().all()
        return tags

    @staticmethod
    def insert_file(session, technology, path):
        """
        Insert a new file related to technology in file table if it does not exist yet.
        """
        stmt = select(File).filter_by(technology=technology, path=path)
        entry = session.execute(stmt).scalar_one_or_none()

        if not entry:
            new_file = File(technology=technology, path=path)
            session.add(new_file)
            logger.info(f"Entry {new_file} added to file database")
        else:
            logger.debug(f"Entry {entry} already exists in files database")

    @staticmethod
    def insert_or_update_hash(session, hash_value, technology, version):
        """
        Insert a new hash related to technology and version in hash table if it does not exist yet.
        If it already exists, update related versions.
        """
        stmt = select(Hash).filter_by(hash=hash_value)
        entry = session.execute(stmt).scalar_one_or_none()

        if not entry:
            new_hash = Hash(hash=hash_value, technology=technology, versions=JSONEncoder() \
                .encode({"versions": [version]}))
            session.add(new_hash)
            logger.info(f"Entry {new_hash} added to hash database")
        else:
            existing_versions = loads(entry.versions)["versions"]

            if version not in existing_versions:
                existing_versions.append(version)
                new_versions = existing_versions
                stmt = update(Hash).where(Hash.hash==hash_value) \
                    .values(versions=JSONEncoder().encode({"versions": new_versions})) \
                        .execution_options(synchronize_session="fetch")
                session.execute(stmt)
                logger.debug(f"Entry {entry} updated with new versions {new_versions}")
            else:
                logger.debug(f"Version {version} already registered for hash {entry.hash}")

    @staticmethod
    def get_all_hashs(session):
        """
        Returns all the hashs already computed.
        """
        stmt = select(Hash)
        hashs = session.execute(stmt).scalars().all()
        return hashs
