pytosql: A python to sqlalchemy converter
==========================================

"It's just sql with extra steps!"

## Installation

    pip install pytosql


## Usage

See tests for a full example. This is just an illustration:


    class Resource(Base):
        id = Column(Integer, primary_key=True)
        name = Column(String)
        labels = relationship("Label", secondary=resources_labels)

    class Label(Base):
        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False)

    from pytosql import python_to_sqlalchemy

    query = python_to_sqlalchemy(Resource, "name == 'R1' and ('L2' in labels or 'C' in labels) and 'L1' in labels")
    for resource in session.scalars(query):
        print(resource)




