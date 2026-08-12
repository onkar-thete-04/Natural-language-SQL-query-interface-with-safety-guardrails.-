from __future__ import annotations


class TextToSQLError(Exception):
    pass


class SchemaIntrospectionError(TextToSQLError):
    pass


class LLMClientError(TextToSQLError):
    pass


class SQLValidationError(TextToSQLError):
    pass


class GuardrailError(TextToSQLError):
    pass


class ExecutionError(TextToSQLError):
    pass