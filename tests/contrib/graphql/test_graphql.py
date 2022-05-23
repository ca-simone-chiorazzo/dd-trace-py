import graphql
import pytest

from ddtrace import tracer
from ddtrace.contrib.graphql import graphql_version
from ddtrace.contrib.graphql import patch
from ddtrace.contrib.graphql import unpatch
from tests.utils import snapshot


if graphql_version == (2,):
    from promise import Promise


@pytest.fixture(autouse=True)
def graphql_patching():
    patch()
    yield
    unpatch()


@pytest.fixture
def test_schema():
    return graphql.GraphQLSchema(
        query=graphql.GraphQLObjectType(
            name="RootQueryType",
            fields={"hello": graphql.GraphQLField(graphql.GraphQLString, None, lambda obj, info: "friend")},
        )
    )


@pytest.fixture
def test_source_str():
    return "{ hello }"


@pytest.fixture
def test_source(test_source_str):
    return graphql.Source(test_source_str)


@pytest.mark.asyncio
@pytest.mark.skipif(graphql_version < (3, 0), reason="graphql.graphql is NOT async in v2.0")
async def test_graphql(test_schema, test_source_str, snapshot_context):
    with snapshot_context():
        result = await graphql.graphql(test_schema, test_source_str)
        assert result.data == {"hello": "friend"}


@pytest.mark.asyncio
@pytest.mark.skipif(graphql_version < (3, 0), reason="graphql.graphql is NOT async in v2.0")
async def test_graphql_sync(test_schema, test_source_str, snapshot_context):
    with snapshot_context(token="tests.contrib.graphql.test_graphql.test_graphql"):
        # Although graphql_sync() is synchronous, it's implementation relies on async calls.
        # In python 3.6, running this test outside of an asyncio fixture produces 5 top level spans instead of one
        # trace with 5 spans (this does not occur in python>3.6).
        result = graphql.graphql_sync(test_schema, test_source_str)
        assert result.data == {"hello": "friend"}


@pytest.mark.asyncio
@pytest.mark.skipif(graphql_version < (3, 0), reason="graphql.graphql_sync is NOT supported in v2.0")
async def test_graphql_error(test_schema, snapshot_context):
    with snapshot_context(ignores=["meta.error.type", "meta.error.msg"]):
        result = graphql.graphql_sync(test_schema, "{ invalid_schema }")
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], graphql.error.GraphQLError)
        assert result.errors[0].message == "Cannot query field 'invalid_schema' on type 'RootQueryType'."


@snapshot(token_override="tests.contrib.graphql.test_graphql.test_graphql")
@pytest.mark.skipif(graphql_version >= (3, 0), reason="graphql.graphql is NOT async in v2.0")
def test_graphql_v2(test_schema, test_source_str):
    result = graphql.graphql(test_schema, test_source_str)
    assert result.data == {"hello": "friend"}


@snapshot(
    token_override="tests.contrib.graphql.test_graphql.test_graphql_error",
    ignores=["meta.error.type", "meta.error.msg"],
)
@pytest.mark.skipif(graphql_version >= (3, 0), reason="graphql.graphql is NOT async in v2.0")
def test_graphql_error_v2(test_schema):
    result = graphql.graphql(test_schema, "{ invalid_schema }")
    assert len(result.errors) == 1
    assert isinstance(result.errors[0], graphql.error.GraphQLError)
    assert result.errors[0].message == 'Cannot query field "invalid_schema" on type "RootQueryType".'


@snapshot(token_override="tests.contrib.graphql.test_graphql.test_graphql")
@pytest.mark.skipif(graphql_version >= (3, 0), reason="graphql.graphql is NOT async in v2.0")
def test_graphql_v2_promise(test_schema, test_source_str):
    p = graphql.graphql(test_schema, test_source_str, return_promise=True)  # type: Promise
    result = p.get()
    assert result.data == {"hello": "friend"}


@snapshot(ignores=["meta.error.type", "meta.error.msg"])
@pytest.mark.skipif(graphql_version >= (3, 0), reason="graphql.graphql is NOT async in v2.0")
def test_graphql_error_v2_promise(test_schema):
    p = graphql.graphql(test_schema, "{ invalid_schema }", return_promise=True)  # type: Promise
    result = p.get()
    assert len(result.errors) == 1
    assert isinstance(result.errors[0], graphql.error.GraphQLError)
    assert result.errors[0].message == 'Cannot query field "invalid_schema" on type "RootQueryType".'


def test_graphql_execute(test_schema, test_source_str):
    with tracer.trace("test-execute-instrumentation"):
        source = graphql.language.source.Source(test_source_str, "GraphQL request")
        ast = graphql.language.parser.parse(source)

        graphql.execute(test_schema, ast)
        graphql.execution.execute(test_schema, ast)


@snapshot(token_override="tests.contrib.graphql.test_graphql.test_graphql_execute")
@pytest.mark.skipif(graphql_version < (3, 1), reason="graphql.execute_sync is not supported in graphql<3.1")
def test_graphql_execute_sync(test_schema, test_source_str):
    with tracer.trace("test-execute-instrumentation"):
        source = graphql.language.source.Source(test_source_str, "GraphQL request")
        ast = graphql.language.parser.parse(source)

        graphql.execute_sync(test_schema, ast)
        graphql.execution.execute_sync(test_schema, ast)
