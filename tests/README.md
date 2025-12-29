# Conventions for tests

## Unit tests
- Always use `unittest.TestCase` for test structure
- Never use mocking functionality that works via decorators -- only use functions that are context managers
- DO NOT write unit tests for trivial assignments like setters, getters, or constructors that assign member variables.
