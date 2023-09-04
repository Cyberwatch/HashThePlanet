"""
This module handles connections and requests to the database
"""
# standard imports
import hashlib
import os
from json import JSONEncoder, loads
from typing import List
from git import Repo

# third party imports
from loguru import logger
from sqlalchemy import JSON, Column, Text, select, update, and_
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.sql.sqltypes import Integer

Base = declarative_base()

class Version(Base):
    """
    This class is a model for version table
    """
    @declared_attr
    def __tablename__(cls): # pylint: disable=no-self-argument
        return cls.__name__.lower()

    rowid = Column(Integer)
    technology = Column(Text, nullable=False, primary_key=True)
    version = Column(Text, nullable=False, primary_key=True)

    def __repr__(self):
        return f"Version (technology={self.technology}, version={self.version})"

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
    file = Column(Text, nullable=False)
    technology = Column(Text, nullable=False)
    versions = Column(JSON, nullable=False)

    @staticmethod
    def hash_file(file_path: str) -> str:
        """
        This method computes the SHA256 hash of the provided file and returns it.
        """
        try:
            with open(file_path, 'rb') as file_descriptor:
                file_bytes = file_descriptor.read() # read entire file as bytes
                readable_hash = hashlib.sha256(file_bytes).hexdigest()
                return readable_hash
        except OSError as error:
            logger.error(f"Error with file {file_path} : {error}")
        return None

    @staticmethod
    def calculate_git_hash(file_path: str) -> str:
        """
        This method computes the Git SHA1 hash of the provided file and returns it.
        """
        repo_path = os.path.dirname(os.path.abspath(file_path))
        repo = Repo.init(repo_path)  # Initialize a Git repository object
        try:
            with open(file_path, "rb"):
                blob_hash = repo.git.hash_object(file_path)  # Calculate the hash
            return blob_hash
        except OSError as error:
            logger.error(f"Error with file {file_path} : {error}")
        return None

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        """
        This method computes the SHA256 hash of the provided data and returns it.
        """
        return hashlib.sha256(data).hexdigest()

    def __repr__(self):
        return f"Hash (hash={self.hash}, technology={self.technology}, versions={self.versions})"

class DbConnector():
    """
    This class implements method to connect to and request the database.
    """
    @staticmethod
    def insert_version(session, technology, version):
        """
        Insert a new version related to technology in version table if it does not exist yet.
        """
        stmt = select(Version).filter_by(technology=technology, version=str(version))
        entry = session.execute(stmt).scalar_one_or_none()

        if not entry:
            new_version = Version(technology=technology, version=str(version))
            session.add(new_version)
            logger.info(f"Entry {new_version} added to version database")
        else:
            logger.debug(f"Entry {entry} already exists in versions database")

    @staticmethod
    def insert_versions(session, technology, versions):
        """
        Insert a list of versions related to technology.
        """
        for _, version in enumerate(versions):
            DbConnector.insert_version(session, technology, version)

    @staticmethod
    def get_versions(session, technology):
        """
        Returns all the versions related to technology.
        """
        stmt = select(Version.version).filter_by(technology=technology).order_by(Version.rowid.asc())
        versions = session.execute(stmt).scalars().all()
        return versions

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
            logger.debug(f"Entry {new_file} added to file database")
        else:
            logger.debug(f"Entry {entry} already exists in files database")

    @staticmethod
    def insert_or_update_hash(session,file_name: str, hash_value: str, technology: str, versions: List[str]):
        """
        Insert a new hash related to technology and version in hash table if it does not exist yet.
        If it already exists, update related versions.
        """
        stmt = select(Hash).filter_by(hash=hash_value)
        entry = session.execute(stmt).scalar_one_or_none()

        if not entry:
            new_hash = Hash(file = file_name, hash=hash_value, technology=technology, versions=JSONEncoder() \
                .encode({"versions": versions}))
            session.add(new_hash)
            logger.debug(f"Entry {new_hash} added to hash database")
        else:
            existing_versions: List[str] = loads(entry.versions)["versions"]


            for version in versions:
                if version not in existing_versions:
                    existing_versions.append(version)
            stmt = update(Hash).where(Hash.hash==hash_value) \
                .values(versions=JSONEncoder().encode({"versions": existing_versions})) \
                    .execution_options(synchronize_session="fetch")
            session.execute(stmt)
            logger.debug(f"Entry {entry} updated with new versions {versions}")

    @staticmethod
    def insert_version_existing_files(session, file_name: str, old_version: str, new_version: str):
        """
        Insert a new hash related to technology and version in hash table if it does not exist yet.
        If it already exists, update related versions.
        """

        stmt = select(Hash).filter(Hash.file ==file_name, Hash.versions.contains(str(old_version)))

        entries = session.execute(stmt).scalars().all()
        if entries:
            for entry in entries:
                existing_versions: List[str] = loads(entry.versions)["versions"]

                if old_version in existing_versions:
                    existing_versions.append(new_version)
                    stmt = update(Hash).where(and_(Hash.file == file_name, Hash.versions.contains(old_version))) \
                        .values(versions=JSONEncoder().encode({"versions": existing_versions})) \
                        .execution_options(synchronize_session="fetch")
                    session.execute(stmt)
                    logger.debug(f"Entry {entry} updated with new versions {existing_versions}")

    @staticmethod
    def get_all_hashs(session):
        """
        Returns all the hashs already computed.
        """
        stmt = select(Hash)
        hashs = session.execute(stmt).scalars().all()
        return hashs

    @staticmethod
    def find_hash(session, hash_str: str):
        """
        Returns a technology and its versions from a hash.
        """
        return session.query(Hash.technology, Hash.versions).filter(Hash.hash == hash_str).first()

    @staticmethod
    def get_static_files(session):
        """
        Returns all files ending with .html, .md or .txt
        """
        static_files_query = session \
                            .query(File.path) \
                            .filter(File.path.regexp_match(r"([a-zA-Z0-9\s_\\.\-\(\):])+(.html|.md|.txt)$"))
        return [path for path, in static_files_query]
