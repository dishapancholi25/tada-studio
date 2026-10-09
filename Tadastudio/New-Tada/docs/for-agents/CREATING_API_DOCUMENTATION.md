# API Module Documentation Template Prompt

Use this prompt to generate comprehensive API documentation for any AgenticStudio API module. Simply replace `{MODULE_NAME}`
with the module you want to document (e.g., `auth`, `execution`, `documents`, etc.).

---

## Prompt Template

```
I need you to create comprehensive API documentation for the {MODULE_NAME} API module in the AgenticStudio backend.

**Module Location:** backend/api/{MODULE_NAME}/

**Documentation Requirements:**

1. **Analyse the Module Structure First:**
   - Read backend/api/{MODULE_NAME}/__init__.py
   - Read backend/api/{MODULE_NAME}/routes.py
   - Read backend/api/{MODULE_NAME}/models.py
   - List all files in backend/api/{MODULE_NAME}/handlers/
   - List all files in backend/api/{MODULE_NAME}/services/ (if exists)
   - Understand the module's purpose and responsibilities

2. **Create Documentation Following This Structure:**

   ## Overview
   - Brief description of module purpose (2-3 sentences)
   - Location and base path
   - Primary responsibilities (bullet list)

   ## Architecture
   ### Module Structure
   - Directory tree showing all files
   - Brief description of each major file's purpose

   ### Design Pattern
   - Diagram showing request flow
   - Explanation of how handlers delegate to services

   ## Authentication & Authorisation (if applicable)
   ### Authentication
   - How authentication works for this module
   - Required headers/tokens
   - User extraction pattern with code example

   ### Authorisation
   - User-scoped data access rules
   - Permission requirements
   - Implementation example

   ## API Endpoints

   For each endpoint, provide:
   - Group endpoints by logical categories
   - For EACH endpoint include:

   ### `{METHOD} {PATH}`

   Brief description of what it does.

   **Authentication:** Required/Optional/None

   **Path Parameters:** (if any)
   - `param_name` - Description

   **Query Parameters:** (if any)
   - `param_name` - Description (default: value)

   **Request Body:** (if any)
   ```json
   {
     "field": "value with realistic example"
   }
   ```

**Response:**

   ```json
   {
     "success": true,
     "data": "realistic response example"
   }
   ```

**Use Cases:**

- When to use this endpoint
- Common scenarios

**Behaviour:**

- What happens internally
- Side effects
- Special considerations

**Validation:** (if applicable)

- Input validation rules
- Constraints

**Errors:** (if notable)

- Common error scenarios
- Error codes specific to this endpoint

## Error Handling

### Error Response Format

- Standard error structure
- Example error response

### Common Error Codes

- List error codes by HTTP status
- Explanation of each error code
- When each error occurs

### Error Handling Example

- Code example showing proper error handling

## Integration with Services Layer

### Dependency Flow

- Diagram showing flow from route → handler → service

### Example Integration

- Code showing a complete example
- Route handler code
- Handler delegation code
- Services used

### Services Used

- List all services this module depends on
- Brief description of each service's role

## Usage Examples

### Complete {Module Purpose} Example

- End-to-end code example
- Multiple endpoint calls showing a complete workflow
- Python or JavaScript examples
- Include error handling

## Performance Considerations

### Endpoint Performance

- Categorise endpoints by speed (fast/medium/slow)
- List endpoints in each category

### Optimisation Tips

- Practical optimisation advice
- Code examples of good vs bad patterns
- Caching strategies (if applicable)

## Related Documentation

- Links to architecture docs
- Links to related API modules
- Links to services documentation

## Summary

- 2-3 paragraph summary of module
- Key features (bullet list)
- Primary use cases

1. **Documentation Style Guidelines:**
    - ✅ Use Australian spelling (organised, authorisation, behaviour, etc.)
    - ✅ Provide realistic JSON examples (not "string", "123" placeholders)
    - ✅ Include complete code examples that could actually run
    - ✅ Use markdown formatting with proper headers
    - ✅ Add code blocks with language syntax highlighting
    - ✅ Cross-reference related documentation
    - ✅ Explain WHY not just WHAT (use cases, rationale)
    - ✅ Include both success and error scenarios
    - ✅ Show integration patterns with services layer

2. **Technical Accuracy:**
    - Read actual source code for accurate endpoint paths
    - Verify HTTP methods from routes.py
    - Check actual Pydantic models for request/response schemas
    - Identify all path/query/body parameters
    - Note authentication requirements from dependencies
    - List all handlers used

3. **Save Documentation:**
   Create the file at: docs/api/{MODULE_NAME}.md

**Example of Quality:**
Reference docs/api/graph.md as the quality benchmark. Match its:

- Comprehensiveness (all endpoints documented)
- Detail level (realistic examples, use cases, validation rules)
- Structure (clear sections, logical grouping)
- Code examples (complete, runnable examples)
- Integration focus (shows connection to services)

Please analyse the module thoroughly and create complete documentation following this structure.

```

---

## Usage Examples

### Example 1: Document Auth Module

```

I need you to create comprehensive API documentation for the auth API module in the AgenticStudio backend.

[... rest of template above ...]

```

### Example 2: Document Execution Module

```

I need you to create comprehensive API documentation for the execution API module in the AgenticStudio backend.

[... rest of template above ...]

```

### Example 3: Document Documents Module

```

I need you to create comprehensive API documentation for the documents API module in the AgenticStudio backend.

[... rest of template above ...]

```

---

## Customisation Tips

### For Smaller Modules
If the module has fewer endpoints (< 10), you can add:
```

Note: This is a smaller module with only {N} endpoints. Focus on detail and integration examples rather than extensive
categorisation.

```

### For Complex Modules
If the module is complex (like graph), you can add:
```

Note: This is a large module with {N}+ endpoints. Organise endpoints into clear logical categories. Provide a table of
contents after the Overview section.

```

### For Modules with Special Features
Add specific instructions:
```

Special focus areas for this module:

- Real-time capabilities (if WebSocket)
- Streaming patterns (if SSE/streaming)
- Background processing (if async)
- File handling (if document processing)
- Security considerations (if auth/credentials)

```

---

## Quality Checklist

After generating documentation, verify:

- [ ] All endpoints from routes.py are documented
- [ ] Request/response examples are realistic and valid JSON
- [ ] Australian spelling throughout
- [ ] Authentication requirements specified for each endpoint
- [ ] Use cases provided for major endpoints
- [ ] Error handling section complete
- [ ] Integration examples show service layer connection
- [ ] Performance considerations included
- [ ] Related documentation linked
- [ ] Code examples are complete and could run
- [ ] Module purpose clearly explained
- [ ] File structure documented

---

## Module Priority Order

Suggested order for documenting remaining modules:

**High Priority** (core functionality):
1. execution - Workflow execution endpoints
2. http_execution - HTTP streaming execution
3. websocket - Real-time WebSocket API
4. execution_history - Execution records and logs

**Medium Priority** (important features):
5. auth - Authentication and authorisation
6. documents - Document upload and processing
7. datasources - Database connections
8. memory - Conversation memory management

**Lower Priority** (supporting features):
9. monitoring - Health checks and diagnostics
10. trace - LangSmith trace integration
11. model_deployments - LLM deployment management
12. checkpoints - Checkpoint management
13. email - Email integration
14. tools - Tool endpoints
15. wiki - Wiki functionality
16. workflow - Workflow publishing

---

## Tips for Success

1. **Let the AI read first:** The prompt instructs reading source files before writing - this ensures accuracy

2. **One module at a time:** Don't try to document multiple modules in one prompt

3. **Verify afterwards:** Spot-check the generated documentation against actual code

4. **Iterate if needed:** If output is incomplete, ask for specific sections to be expanded

5. **Keep examples realistic:** Real endpoint paths, real field names, realistic data values

6. **Update template:** If you find gaps in the template, update this file for future use
