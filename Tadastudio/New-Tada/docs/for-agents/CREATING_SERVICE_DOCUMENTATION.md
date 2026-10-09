# Service Documentation Template Prompt

I need you to create comprehensive service layer documentation for the {MODULE_NAME} service module in the AgenticStudio
backend.

**Module Location:** backend/services/{MODULE_NAME}/

**Documentation Requirements:**

1. **Analyse the Module Structure First:**
    - Read backend/services/{MODULE_NAME}/**init**.py to understand exports
    - List all Python files in backend/services/{MODULE_NAME}/
    - List all subdirectories and their purpose
    - Identify all classes, functions, constants, and exceptions
    - Understand dependencies on other services
    - Check for providers, handlers, factories, or other patterns

2. **Create Documentation Following This Structure:**

   ## Overview

    - Brief description of module purpose (2-3 sentences)
    - Location in codebase
    - Primary responsibilities (bullet list)
    - Key use cases

   ## Architecture

   ### Module Structure

    - Directory tree showing all files and subdirectories
    - Brief description of each major file's purpose
    - Explanation of subdirectory organisation (e.g., providers/, handlers/, factories/)

   ### Design Patterns

    - Architectural patterns used (Factory, Strategy, Singleton, etc.)
    - Dependency injection patterns
    - How the service integrates with the broader system
    - Diagram showing component relationships

   ### Dependencies

    - Internal dependencies (other backend.services modules)
    - External dependencies (third-party libraries)
    - Database dependencies (if applicable)
    - Environment variables and configuration

   ## Public API

   ### Exported Classes

   List all classes exported in `__all__` with brief descriptions:
    - `ClassName` - One-line description of purpose

   ### Exported Functions

   List all functions exported in `__all__` with brief descriptions:
    - `function_name()` - One-line description of purpose

   ### Constants and Configuration

   List all exported constants, enums, or config values:
    - `CONSTANT_NAME` - Description and default value

   ### Exceptions

   List all custom exceptions with their hierarchy:

   ```
   BaseServiceException
   ├── SpecificError1
   ├── SpecificError2
   └── SpecificError3
   ```

   ## Core Classes

   For each major class, provide:

   ### `ClassName`

   Brief description of what this class does.

   **Purpose:** What problem does this class solve?

   **Responsibilities:**
    - Responsibility 1
    - Responsibility 2
    - Responsibility 3

   **Initialisation:**

   ```python
   def __init__(
       self,
       param1: Type1,
       param2: Type2 = default_value,
   ) -> None:
       """
       Args:
           param1: Description
           param2: Description (default: value)
       """
   ```

   **Key Methods:**

   #### `method_name()`

   ```python
   def method_name(
       self,
       arg1: Type1,
       arg2: Type2,
   ) -> ReturnType:
       """Brief description of what this method does."""
   ```

   **Parameters:**
    - `arg1` (Type1) - Description
    - `arg2` (Type2) - Description

   **Returns:**
    - `ReturnType` - Description of return value

   **Raises:**
    - `ExceptionType` - When this error occurs

   **Example:**

   ```python
   # Realistic example showing method usage
   service = ClassName(param1=value1, param2=value2)
   result = service.method_name(arg1=example1, arg2=example2)
   ```

   **Behaviour:**
    - What happens internally
    - Side effects
    - State changes
    - Special considerations

   **Use Cases:**
    - When to use this method
    - Common scenarios
    - Best practices

   [Repeat for all public methods]

   **Class Attributes:**
    - `attribute_name: Type` - Description

   **Properties:**
    - `property_name: Type` - Description (read-only/read-write)

   [Repeat for all major classes]

   ## Functions

   For each standalone function exported by the module:

   ### `function_name()`

   Brief description of what this function does.

   **Signature:**

   ```python
   def function_name(
       param1: Type1,
       param2: Type2,
       param3: Optional[Type3] = None,
   ) -> ReturnType:
       """Docstring here."""
   ```

   **Parameters:**
    - `param1` (Type1) - Description
    - `param2` (Type2) - Description
    - `param3` (Optional[Type3]) - Description (default: None)

   **Returns:**
    - `ReturnType` - Description

   **Raises:**
    - `ExceptionType` - When this error occurs

   **Example:**

   ```python
   # Realistic usage example
   result = function_name(
       param1=value1,
       param2=value2,
   )
   ```

   **Use Cases:**
    - When to use this function
    - Common scenarios

   [Repeat for all major functions]

   ## Configuration

   ### Configuration Classes

   Document any config classes or Pydantic models:

   ```python
   class ConfigClassName:
       """Description."""

       field1: Type1 = default
       field2: Type2 = default
   ```

   **Fields:**
    - `field1` - Description (default: value)
    - `field2` - Description (default: value)

   ### Environment Variables

   List all environment variables used:
    - `ENV_VAR_NAME` - Description (default: value, required: yes/no)

   ### Initialisation Patterns

   Show how to properly initialise the service:

   **Basic Initialisation:**

   ```python
   from backend.services.{MODULE_NAME} import MainClass

   service = MainClass()
   ```

   **Advanced Initialisation:**

   ```python
   from backend.services.{MODULE_NAME} import MainClass, ConfigClass

   config = ConfigClass(
       setting1=value1,
       setting2=value2,
   )
   service = MainClass(config=config)
   ```

   **Dependency Injection:**

   ```python
   # Show how this service is typically injected
   ```

   ## Error Handling

   ### Exception Hierarchy

   Visual representation of exception inheritance:

   ```
   Exception
   └── BaseModuleException
       ├── ConfigurationError
       ├── ValidationError
       │   ├── InvalidInputError
       │   └── MissingFieldError
       └── OperationError
           ├── ConnectionError
           └── TimeoutError
   ```

   ### Exception Details

   For each exception:

   #### `ExceptionName`

   Brief description of when this exception is raised.

   **Inherits from:** `ParentException`

   **When raised:**
    - Scenario 1
    - Scenario 2

   **Example:**

   ```python
   try:
       service.method()
   except ExceptionName as e:
       # Handle specific error
       logger.error(f"Error: {e}")
   ```

   ### Error Handling Patterns

   ```python
   # Recommended error handling pattern
   from backend.services.{MODULE_NAME} import Service, ServiceError

   try:
       service = Service()
       result = service.process(data)
   except ValidationError as e:
       # Handle validation errors
       return {"error": "Invalid input", "details": str(e)}
   except OperationError as e:
       # Handle operation errors
       logger.error(f"Operation failed: {e}")
       raise
   except ServiceError as e:
       # Handle general service errors
       logger.error(f"Service error: {e}")
       raise
   ```

   ## Integration Patterns

   ### Integration with API Layer

   Show how API modules use this service:

   ```python
   # Example from backend/api/module/routes.py
   from fastapi import APIRouter, Depends
   from backend.services.{MODULE_NAME} import Service

   router = APIRouter()

   @router.post("/endpoint")
   async def endpoint(data: InputModel) -> OutputModel:
       service = Service()
       result = service.process(data)
       return result
   ```

   ### Integration with Other Services

   Show how this service depends on or integrates with other services:

   ```python
   from backend.services.{MODULE_NAME} import MainService
   from backend.services.other_service import OtherService

   # Example integration pattern
   main_service = MainService()
   other_service = OtherService()

   # Show how they work together
   data = other_service.fetch_data(id=123)
   result = main_service.process(data)
   ```

   ### Dependency Flow

   Diagram or description showing:
    - What services this module depends on
    - What services depend on this module
    - Data flow between services

   ### Common Integration Patterns

   #### Pattern 1: [Pattern Name]

   ```python
   # Example showing this pattern
   ```

   #### Pattern 2: [Pattern Name]

   ```python
   # Example showing this pattern
   ```

   ## Usage Examples

   ### Example 1: Basic Usage

   Complete end-to-end example of basic usage:

   ```python
   from backend.services.{MODULE_NAME} import MainClass

   # Step 1: Initialise
   service = MainClass()

   # Step 2: Use the service
   result = service.method(param="value")

   # Step 3: Process result
   print(f"Result: {result}")
   ```

   ### Example 2: Advanced Usage

   Complete example showing advanced features:

   ```python
   from backend.services.{MODULE_NAME} import (
       MainClass,
       ConfigClass,
       HelperFunction,
   )

   # Advanced configuration
   config = ConfigClass(
       setting1=value1,
       setting2=value2,
   )

   # Initialise with config
   service = MainClass(config=config)

   # Use advanced features
   result = service.advanced_method(
       param1=value1,
       param2=value2,
   )

   # Use helper function
   processed = HelperFunction(result)
   ```

   ### Example 3: Complete Workflow

   Show a realistic, complete workflow:

   ```python
   # Complete example showing typical usage in application
   from backend.services.{MODULE_NAME} import (
       Service,
       ServiceError,
       ValidationError,
   )
   from backend.services.database import get_db_session

   async def complete_workflow_example():
       """Example showing complete workflow."""

       # Setup
       service = Service()

       try:
           # Step 1: Fetch data
           data = await service.fetch(id="example-123")

           # Step 2: Process data
           processed = service.process(data)

           # Step 3: Validate result
           validated = service.validate(processed)

           # Step 4: Save to database
           db = get_db_session()
           service.save(db, validated)

           return {"success": True, "data": validated}

       except ValidationError as e:
           logger.error(f"Validation failed: {e}")
           return {"success": False, "error": str(e)}
       except ServiceError as e:
           logger.error(f"Service error: {e}")
           raise
   ```

   ### Example 4: Testing Usage

   Show how to use this service in tests:

   ```python
   import pytest
   from backend.services.{MODULE_NAME} import Service, ServiceError

   def test_service_basic_usage():
       """Test basic service usage."""
       service = Service()
       result = service.method(param="test")
       assert result is not None

   def test_service_error_handling():
       """Test service error handling."""
       service = Service()
       with pytest.raises(ServiceError):
           service.method(param="invalid")
   ```

   ## Performance Considerations

   ### Performance Characteristics

    - Complexity analysis of key operations (O(n), O(1), etc.)
    - Memory usage patterns
    - I/O characteristics (CPU-bound, I/O-bound, network-bound)

   ### Optimisation Tips

   #### Tip 1: [Optimisation Name]

   **Problem:**

   ```python
   # Inefficient pattern
   for item in items:
       service.process_one(item)  # Multiple calls
   ```

   **Solution:**

   ```python
   # Efficient pattern
   service.process_batch(items)  # Single batch call
   ```

   #### Tip 2: Caching (if applicable)

   ```python
   from functools import lru_cache

   @lru_cache(maxsize=128)
   def expensive_operation(key: str) -> Result:
       """Cached expensive operation."""
       return service.compute(key)
   ```

   ### Async/Await Support

   If the service supports async operations:

   ```python
   from backend.services.{MODULE_NAME} import AsyncService

   async def example():
       service = AsyncService()
       result = await service.async_method(param="value")
       return result
   ```

   ### Connection Pooling (if applicable)

   ```python
   # Show connection pooling patterns if relevant
   ```

   ### Batch Operations

   ```python
   # Show batch operation patterns if available
   service.process_batch(items)  # More efficient than loop
   ```

   ## Testing Patterns

   ### Unit Testing

   ```python
   import pytest
   from unittest.mock import Mock, patch
   from backend.services.{MODULE_NAME} import Service

   @pytest.fixture
   def service():
       """Service fixture."""
       return Service()

   def test_method(service):
       """Test method behaviour."""
       result = service.method(param="test")
       assert result.success is True
   ```

   ### Mocking Dependencies

   ```python
   @patch('backend.services.{MODULE_NAME}.dependency')
   def test_with_mock(mock_dependency, service):
       """Test with mocked dependency."""
       mock_dependency.return_value = expected_value
       result = service.method()
       assert result == expected_value
   ```

   ### Integration Testing

   ```python
   @pytest.mark.integration
   async def test_integration():
       """Integration test example."""
       # Test with real dependencies
       pass
   ```

   ## Best Practices

   ### Do's

    - ✅ Best practice 1 with code example
    - ✅ Best practice 2 with code example
    - ✅ Best practice 3 with code example

   ### Don'ts

    - ❌ Anti-pattern 1 with explanation
    - ❌ Anti-pattern 2 with explanation
    - ❌ Anti-pattern 3 with explanation

   ## Related Documentation

   ### Related Services

    - [Service 1](./service1.md) - Brief description
    - [Service 2](./service2.md) - Brief description

   ### Related API Modules

    - [API Module 1](../agents-guide/api/module1.md) - Brief description
    - [API Module 2](../agents-guide/api/module2.md) - Brief description

   ### Architecture Documentation

    - [Architecture Doc](../architecture/doc.md) - Brief description

   ### External Documentation

    - [Library/Framework docs](https://example.com) - If relevant

   ## Summary

   2-3 paragraph summary of the service module:
    - What it does
    - Why it exists
    - How it fits into the system

   **Key Features:**
    - Feature 1
    - Feature 2
    - Feature 3

   **Primary Use Cases:**
    - Use case 1
    - Use case 2
    - Use case 3

   **When to Use This Service:**
    - Scenario 1
    - Scenario 2

3. **Documentation Style Guidelines:**
    - ✅ Use Australian spelling (organised, initialise, behaviour, etc.)
    - ✅ Provide realistic code examples (not placeholder values)
    - ✅ Include complete code examples that could actually run
    - ✅ Use markdown formatting with proper headers
    - ✅ Add code blocks with Python syntax highlighting
    - ✅ Cross-reference related documentation
    - ✅ Explain WHY not just WHAT (use cases, rationale)
    - ✅ Include both basic and advanced usage
    - ✅ Show integration patterns with other services
    - ✅ Include type hints in all code examples
    - ✅ Show error handling patterns
    - ✅ Focus on practical, real-world usage

4. **Technical Accuracy:**
    - Read actual source code for accurate class/function signatures
    - Verify type hints and return types
    - Check actual dependencies from imports
    - Identify all exported symbols from `__all__`
    - Document all public methods and functions
    - List all custom exceptions
    - Show realistic usage examples
    - Include proper error handling

5. **Save Documentation:**
   Create the file at: docs/services/{MODULE_NAME}.md

**Example of Quality:**
Reference docs/api/graph.md as a quality benchmark for structure, detail level, and comprehensiveness. Adapt its:

- Comprehensiveness (all public APIs documented)
- Detail level (realistic examples, use cases, best practices)
- Structure (clear sections, logical grouping)
- Code examples (complete, runnable examples)
- Integration focus (shows connection to other services)

Please analyse the module thoroughly and create complete documentation following this structure.

```

---

## Usage Examples

### Example 1: Document Auth Service

```

I need you to create comprehensive service layer documentation for the auth service module in the AgenticStudio backend.

**Module Location:** backend/services/auth/

[... rest of template above ...]

```

### Example 2: Document Execution Service

```

I need you to create comprehensive service layer documentation for the execution service module in the AgenticStudio
backend.

**Module Location:** backend/services/execution/

[... rest of template above ...]

```

### Example 3: Document Document Service

```

I need you to create comprehensive service layer documentation for the document service module in the AgenticStudio backend.

**Module Location:** backend/services/document/

[... rest of template above ...]

```

---

## Customisation Tips

### For Simple Services
If the service is simple (single class, few methods):
```

Note: This is a focused service with a single main class. Emphasise clarity and practical examples over extensive
categorisation.

```

### For Complex Services
If the service is complex (multiple classes, submodules, factories):
```

Note: This is a large service module with multiple components. Provide a table of contents after the Overview section.
Organise components by responsibility.

```

### For Services with Providers
If the service uses provider pattern:
```

Special focus: Document the provider pattern, showing how to:

- Implement custom providers
- Register providers
- Switch between providers
- Configure provider-specific options

```

### For Services with Factory Patterns
```

Special focus: Document factory patterns:

- How to use factory functions
- When to use each factory
- Factory configuration options
- Custom factory implementations

```

### For Services with Async Support
```

Special focus: Document async/await patterns:

- Async vs sync methods
- Concurrency considerations
- Async context managers
- Error handling in async code

```

---

## Module Priority Order

Suggested order for documenting service modules:

**High Priority** (core business logic):
1. execution - Workflow and agent execution
2. graph - Graph building and management
3. auth - Authentication and authorisation
4. database - Database operations and migrations
5. agent - Agent compilation and execution

**Medium Priority** (important features):
6. document - Document processing
7. datasource - Database connections
8. memory - Conversation memory
9. llm_models - LLM provider management
10. workflow - Workflow publishing and state
11. checkpoint - Checkpoint management

**Lower Priority** (supporting features):
12. email - Email integration
13. search - Web search functionality
14. trace - LangSmith tracing
15. model_deployment - Model deployment management
16. websocket - WebSocket connection management
17. tools - Tool creation and execution
18. metrics - Metrics collection and export
19. ocr - OCR processing
20. text_splitting - Text splitting strategies

---

## Quality Checklist

After generating documentation, verify:

- [ ] All exported classes documented with methods
- [ ] All exported functions documented with signatures
- [ ] Code examples are realistic and include type hints
- [ ] Australian spelling throughout
- [ ] Exception hierarchy clearly shown
- [ ] Dependencies on other services documented
- [ ] Integration examples show service layer connections
- [ ] Performance considerations included
- [ ] Testing patterns provided
- [ ] Related documentation linked
- [ ] Code examples are complete and could run
- [ ] Module purpose clearly explained
- [ ] Directory structure documented
- [ ] Configuration options explained
- [ ] Best practices and anti-patterns included

---

## Tips for Success

1. **Read `__init__.py` first:** This shows the public API and exports

2. **Check for patterns:** Look for providers/, factories/, handlers/ subdirectories indicating design patterns

3. **One service at a time:** Don't try to document multiple services in one prompt

4. **Focus on usage:** Show how other code actually uses this service, not just what it does

5. **Include type hints:** Always show parameter and return types

6. **Show error handling:** Every example should include proper error handling

7. **Real-world examples:** Use realistic parameter values and scenarios

8. **Integration focus:** Show how this service integrates with others

9. **Keep it practical:** Focus on what developers need to know to use the service

10. **Update template:** If you find gaps in the template, update this file for future use

---

## Differences from API Documentation

This template differs from API documentation in key ways:

| API Documentation | Service Documentation |
|------------------|----------------------|
| HTTP endpoints | Classes and functions |
| Request/response JSON | Function parameters/returns |
| Route handlers | Method signatures |
| Query/path parameters | Function arguments |
| Authentication headers | Service dependencies |
| API integration examples | Code usage examples |
| cURL/HTTP examples | Python import/usage |

**Focus on:**
- How to import and use the service
- What classes and methods are available
- How to handle errors
- How to integrate with other services
- Performance and testing considerations
