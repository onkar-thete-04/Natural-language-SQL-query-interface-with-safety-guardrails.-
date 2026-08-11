from schema_engine.models import ColumnInfo, TableInfo, Schema
from prompt_builder.constructor import PromptConstructor


class FakeFewShotLoader:
    def select(self, relevant_tables=None, top_n=4):
        class FakeExample:
            def __init__(self, q, s):
                self.question = q
                self.sql = s

            def as_prompt_block(self):
                return f"Question: {self.question}\nSQL: {self.sql}"

        return [
            FakeExample("Find by id", "SELECT * FROM t WHERE id = 1;"),
            FakeExample("Count rows", "SELECT COUNT(*) FROM t;"),
        ]


class FakeSettings:
    sql_gen_model = "test-model"
    judge_model = "test-judge"
    nvidia_api_key = "fake-key"
    nvidia_base_url = "https://fake.api.com/v1"
    db_url = "postgresql://fake"
    embedding_model = "test-embedding"
    similarity_threshold = 0.3


def test_constructor_includes_schema_context():
    col = ColumnInfo("customer_id", "integer", True, False)
    table = TableInfo("customer", [col], [], {"customer_id": [1, 2]})
    schema = Schema(tables=[table])
    constructor = PromptConstructor(schema, FakeFewShotLoader(), FakeSettings())
    prompt = constructor.build(
        question="find all customers", relevant_tables=["customer"]
    )
    assert "find all customers" in prompt
    assert "customer" in prompt
    assert "customer_id" in prompt


def test_constructor_includes_few_shot_examples():
    table = TableInfo("t", [ColumnInfo("id", "integer", True, False)], [], {})
    schema = Schema(tables=[table])
    constructor = PromptConstructor(schema, FakeFewShotLoader(), FakeSettings())
    prompt = constructor.build(question="test", relevant_tables=["t"])
    assert "Find by id" in prompt
    assert "Count rows" in prompt


def test_constructor_includes_constraint():
    table = TableInfo("t", [ColumnInfo("id", "integer", True, False)], [], {})
    schema = Schema(tables=[table])
    constructor = PromptConstructor(schema, FakeFewShotLoader(), FakeSettings())
    prompt = constructor.build(
        question="find revenue",
        relevant_tables=["t"],
        constraint="Use payment.amount AS revenue.",
    )
    assert "payment.amount" in prompt


def test_constructor_includes_clarification_context():
    table = TableInfo("t", [ColumnInfo("id", "integer", True, False)], [], {})
    schema = Schema(tables=[table])
    constructor = PromptConstructor(schema, FakeFewShotLoader(), FakeSettings())
    prompt = constructor.build(
        question="find revenue",
        relevant_tables=["t"],
        clarifications="The user selected: Gross Revenue",
    )
    assert "Gross Revenue" in prompt
