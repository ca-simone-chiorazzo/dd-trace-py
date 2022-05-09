import pytest

import ddtrace


# patch graphql-core before importing graphene
ddtrace.patch(graphql=True)
import graphene  # noqa: E402


@pytest.fixture
def test_source_str():
    return """
    query something{
      patron {
        id
        name
        age
      }
    }
"""


@pytest.fixture
def test_schema():
    class Patron(graphene.ObjectType):
        id = graphene.ID()
        name = graphene.String()
        age = graphene.Int()

    class Query(graphene.ObjectType):
        patron = graphene.Field(Patron)

        def resolve_patron(root, info):
            return Patron(id=1, name="Syrus", age=27)

    return graphene.Schema(query=Query)


@pytest.mark.snapshot
@pytest.mark.asyncio
@pytest.mark.skipif(graphene.VERSION < (3, 0, 0), reason="execute_async is only supported in graphene>=3.0")
async def test_schema_execute_async(test_schema, test_source_str):
    result = await test_schema.execute_async(test_source_str)
    assert not result.errors
    assert result.data == {"patron": {"id": "1", "name": "Syrus", "age": 27}}


@pytest.mark.snapshot
def test_schema_execute(test_schema, test_source_str):
    result = test_schema.execute(test_source_str)
    assert not result.errors
    assert result.data == {"patron": {"id": "1", "name": "Syrus", "age": 27}}
