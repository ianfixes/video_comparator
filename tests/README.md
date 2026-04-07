# Conventions for tests

## Unit tests
- Always use `unittest.TestCase` for test structure
- Never use mocking functionality that works via decorators -- only use functions that are context managers
- DO NOT write unit tests for trivial assignments like setters, getters, or constructors/dataclasses that only assign member variables to the values passed in.
  - If a test only verifies that `obj.field == value` where `value` was the input to the constructor, it's testing trivial assignment and should be removed.
  - Only test constructors/initializers if they contain actual logic (validation, transformation, computation, side effects, etc.).
  - **Example of trivial test to avoid**: Creating a dataclass with `KeyBinding(key_code=5, ...)` and then asserting `binding.key_code == 5`. This just verifies Python/dataclasses work, not the code's behavior.
