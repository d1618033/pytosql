# pylint: disable=redefined-outer-name,unused-argument

import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, Table, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship  # pylint: disable=no-name-in-module

import pytosql

Base = declarative_base()

resources_labels = Table(
    "resources_labels",
    Base.metadata,
    Column("resource_id", ForeignKey("resources.id")),
    Column("label_id", ForeignKey("labels.id")),
)


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    labels = relationship("Label", secondary=resources_labels)

    def __repr__(self):
        return f"Resource(id={self.id!r}, name={self.name!r})"


class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    def __repr__(self):
        return f"Label(id={self.id!r}, name={self.name!r})"


@pytest.fixture
def session():
    engine = create_engine("sqlite://", echo=True, future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:  # pylint: disable=not-context-manager
        yield session


@pytest.fixture
def labels(session):
    labels = [Label(name="L1"), Label(name="L2"), Label(name="C")]
    session.add_all(labels)
    session.commit()
    return labels


@pytest.fixture
def resources(session, labels):
    resources = [
        Resource(name="R1", labels=[labels[0], labels[2]]),
        Resource(name="R2", labels=[labels[1], labels[2]]),
    ]
    session.add_all(resources)
    session.commit()
    return resources


@pytest.mark.parametrize(
    "query,expected",
    [
        ("'L1' in labels", ["R1"]),
        ("'L2' in labels", ["R2"]),
        ("'C' in labels", ["R1", "R2"]),
        ("'L1' not in labels", ["R2"]),
        ("'L2' not in labels", ["R1"]),
        ("'C' not in labels", []),
        ("name == 'R1'", ["R1"]),
        ("name == 'R2'", ["R2"]),
        ("name != 'R1'", ["R2"]),
        ("name != 'R2'", ["R1"]),
        ("name == 'R1' and 'L1' in labels", ["R1"]),
        ("name == 'R1' and 'L2' in labels", []),
        ("name == 'R1' or 'L2' in labels", ["R1", "R2"]),
        ("(name == 'R1' and 'L1' in labels) or name == 'R2'", ["R1", "R2"]),
        ("(name == 'R1' and 'L2' in labels) or name == 'R2'", ["R2"]),
        (
            "(name == 'R1' and ('L2' in labels or 'C' in labels)) and 'L1' in labels",
            ["R1"],
        ),
    ],
)
def test_python_to_sqlalchemy(session, resources, query, expected):
    assert sorted(
        [resource.name for resource in session.scalars(pytosql.python_to_sqlalchemy(Resource, query))]
    ) == sorted(expected)


def test_syntax_error(session):
    with pytest.raises(pytosql.PyToSQLParsingError, match="Invalid syntax in query `name <> 'hi'`"):
        pytosql.python_to_sqlalchemy(Resource, "name <> 'hi'")
