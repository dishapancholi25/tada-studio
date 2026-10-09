# MCP Server Security Configuration

This document describes the security measures implemented for MCP (Model Context Protocol) stdio server execution.

## Overview

MCP stdio servers allow executing commands on the backend server to run MCP server processes. To mitigate command injection risks, we've implemented a two-layer security approach:

1. **Command Allowlist** - Only specific runtime commands are permitted
2. **Input Validation** - Shell metacharacters are blocked from commands and arguments

## Security Layers

### Layer 1: Command Allowlist

Only the following commands are permitted for stdio MCP servers:

- `npx` - Node.js package executor
- `node` - Node.js runtime
- `python`, `python3`, `python3.11`, `python3.12` - Python runtimes
- `uvx`, `uv` - Python UV package tool
- `deno` - Deno runtime
- `bun` - Bun runtime
- `tsx`, `ts-node` - TypeScript runtimes

**Why this works:**

- Blocks execution of dangerous system commands (`rm`, `bash`, `sh`, `curl`, etc.)
- Permits only legitimate MCP server runtimes
- Easy to extend for new runtimes
- Base command name extracted from paths (handles `/usr/bin/node` → `node`)

**Implementation:**

- `backend/api/user_settings/models.py`
  - `StandardMcpServerConfig.validate_command()`
  - `McpServerConfigRequest.validate_command()`

### Layer 2: Input Validation

All commands and arguments are validated to prevent shell metacharacter injection.

**Blocked metacharacters in commands:**

- `;` - Command chaining
- `|` - Piping
- `&` - Background execution
- `$` - Variable expansion
- `` ` `` - Command substitution
- `\n`, `\r` - Newline injection
- `>`, `<` - Redirection
- `(`, `)` - Subshells

**Blocked metacharacters in arguments:**

- `;`, `|`, `&`, `$`, `` ` ``, `\n`, `\r`

**Why this works:**

- Prevents command injection even if allowlist is bypassed
- Protects against argument-based injection attacks
- Clear error messages guide users to fix issues

**Implementation:**

- Same files as Layer 1
  - `StandardMcpServerConfig.validate_args()`
  - `McpServerConfigRequest.validate_args()`

## Defense in Depth

Both layers work together:

1. **Allowlist stops arbitrary binaries** - Can't execute `/bin/bash` or other system tools
2. **Validation stops injection** - Can't use `node; rm -rf /` or similar attacks
3. **No shell invocation** - Commands executed directly without shell (no `shell=True`)

Even if an attacker finds a way around one layer, the other provides protection.

## Deployment Considerations

### Docker

The allowlist and validation work seamlessly in Docker with no special configuration:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    # No special security settings needed
```

### Kubernetes

The security measures work perfectly in Kubernetes and are **compatible with Pod Security Standards**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: agentic-studio-backend
spec:
  # Recommended security context
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault

  containers:
  - name: backend
    image: your-registry/agentic-studio-backend:latest

    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: ["ALL"]
      runAsNonRoot: true
      runAsUser: 1000

    resources:
      limits:
        memory: "2Gi"
        cpu: "1000m"
        ephemeral-storage: "1Gi"
```

**See `k8s-mcp-security.yaml`** for complete Kubernetes security configuration including:

- SecurityContext best practices
- Resource limits
- NetworkPolicy for network isolation
- Non-root user execution

### Additional Kubernetes Security

Consider layering these Kubernetes features:

1. **NetworkPolicy** - Restrict which services MCP servers can access
2. **Resource Limits** - Prevent resource exhaustion attacks
3. **PodSecurityPolicy/Standards** - Enforce security constraints
4. **ReadOnlyRootFilesystem** - Prevent file system tampering (may break some MCP servers)

## Security Best Practices

### For Administrators

1. **Review the allowlist** periodically and remove unused runtimes
2. **Monitor MCP server creation** via audit logs (when implemented)
3. **Limit MCP server creation** to trusted users (consider admin-only mode)
4. **Use Kubernetes NetworkPolicy** to restrict network access
5. **Enforce resource limits** to prevent DoS attacks

### For Users

1. **Only install trusted MCP servers** from reputable sources
2. **Review MCP server code** before installation when possible
3. **Use environment variables** for secrets (via `secret://` refs)
4. **Test in development** before deploying to production
5. **Report suspicious behavior** to administrators

### For Developers

1. **Never bypass validators** - They're critical security controls
2. **Audit subprocess calls** - Ensure no `shell=True` usage
3. **Log security decisions** - Helps with debugging and auditing
4. **Test with malicious input** - Try to break the validators

## Configuration via Environment Variables

You can customize the security rules without modifying code using environment variables.

### MCP_ALLOWED_COMMANDS

Comma-separated list of allowed commands for stdio MCP servers.

**Default**: `npx,node,python,python3,python3.11,python3.12,uvx,uv,deno,bun,tsx,ts-node`

**Example - Add Ruby support**:

```bash
MCP_ALLOWED_COMMANDS=npx,node,python,python3,ruby
```

**Example - Restrict to only Node.js**:

```bash
MCP_ALLOWED_COMMANDS=npx,node
```

⚠️ **Security Note**: Only add trusted commands. Every command you add increases the attack surface.

### MCP_DANGEROUS_CHARS_COMMAND

String of characters to block in command names.

**Default**: `;|&$`\n\r><()`

**Example - Also block curly braces**:

```bash
MCP_DANGEROUS_CHARS_COMMAND=';|&$`\n\r><(){}
```

⚠️ **Warning**: Removing characters from the default reduces security. Only modify if absolutely necessary.

### MCP_DANGEROUS_CHARS_ARGS

String of characters to block in command arguments.

**Default**: `;|&$`\n\r`

**Example - Also block equals signs**:

```bash
MCP_DANGEROUS_CHARS_ARGS=';|&$`\n\r='
```

⚠️ **Warning**: Removing characters from the default reduces security. Only modify if absolutely necessary.

### Configuration Best Practices

1. **Use environment variables** instead of modifying code - easier to audit and revert
2. **Add to `.env` file** - keeps configuration in one place
3. **Document changes** - comment why you modified the defaults
4. **Test thoroughly** - ensure your changes don't break existing MCP servers
5. **Review regularly** - remove unused commands periodically

### Example Configuration

```bash
# .env file

# Add support for Go-based MCP servers
MCP_ALLOWED_COMMANDS=npx,node,python,python3,uvx,uv,deno,bun,go

# Block additional characters for extra security
MCP_DANGEROUS_CHARS_COMMAND=';|&$`\n\r><(){}[]'
MCP_DANGEROUS_CHARS_ARGS=';|&$`\n\r='
```

## Extending the Allowlist (Legacy Method)

If you prefer to modify code directly:

1. **Edit** `backend/api/user_settings/models.py`
2. **Modify the defaults** in `_get_allowed_commands()`:

   ```python
   # Secure defaults - legitimate MCP server runtimes
   return {
       'npx', 'node', 'python', 'python3',
       'your-new-runtime',  # Add here
   }
   ```

3. **Test thoroughly** with the new runtime
4. **Document** in this file and in code comments

⚠️ **Recommendation**: Use environment variables instead of code changes for easier management.

## Testing

### Command Allowlist

```bash
# This should be REJECTED
curl -X POST http://localhost:8000/api/user-settings/mcp-servers \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "malicious",
    "connection_type": "stdio",
    "command": "bash",
    "args": ["-c", "rm -rf /"],
    "auth_type": "none"
  }'

# Expected error: "Command 'bash' is not in the allowlist"
```

### Metacharacter Blocking

```bash
# This should be REJECTED
curl -X POST http://localhost:8000/api/user-settings/mcp-servers \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "injection",
    "connection_type": "stdio",
    "command": "node; rm -rf /",
    "auth_type": "none"
  }'

# Expected error: "Command contains dangerous shell metacharacter ';'"
```

### Argument Injection

```bash
# This should be REJECTED
curl -X POST http://localhost:8000/api/user-settings/mcp-servers \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "arg-injection",
    "connection_type": "stdio",
    "command": "npx",
    "args": ["server.js", "&&", "curl", "evil.com"],
    "auth_type": "none"
  }'

# Expected error: "Argument at index 1 contains dangerous shell metacharacter '&'"
```

### Valid Configuration

```bash
# This should be ACCEPTED
curl -X POST http://localhost:8000/api/user-settings/mcp-servers \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "filesystem",
    "connection_type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    "auth_type": "none"
  }'

# Expected: Success response with server details
```

### Testing Custom Configuration

```bash
# Set custom allowed commands
export MCP_ALLOWED_COMMANDS=npx,node,ruby

# Restart backend to pick up new config
docker-compose restart backend

# Test Ruby command (should now be ACCEPTED)
curl -X POST http://localhost:8000/api/user-settings/mcp-servers \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "ruby-mcp",
    "connection_type": "stdio",
    "command": "ruby",
    "args": ["server.rb"],
    "auth_type": "none"
  }'

# Expected: Success (ruby is now in allowlist)

# Test Python command (should be REJECTED - not in custom allowlist)
curl -X POST http://localhost:8000/api/user-settings/mcp-servers \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "python-mcp",
    "connection_type": "stdio",
    "command": "python",
    "args": ["server.py"],
    "auth_type": "none"
  }'

# Expected: Error - "Command 'python' is not in the allowlist"
```

## Troubleshooting

### Command Rejected

**Symptom**: "Command 'X' is not in the allowlist"

**Solution**: Either:

1. Use an allowed runtime (check the allowlist above)
2. Add your runtime to the allowlist (see "Extending the Allowlist")
3. Verify the command name (e.g., use `python3` not `/usr/bin/python3`)

### Metacharacter Error

**Symptom**: "Command contains dangerous shell metacharacter"

**Solution**:

- Remove shell metacharacters from command/args
- Don't try to chain commands - use a single MCP server per configuration
- Pass complex logic via environment variables instead

### Command Not Found

**Symptom**: MCP server fails to start with "Command not found"

**Solution**:

1. Ensure the runtime is installed in the container (Node.js, Python, etc.)
2. Check the Dockerfile includes necessary installations
3. Verify the command is in PATH inside the container

## Architecture Decisions

### Why Command Allowlist?

Balances security and usability:

- ✅ Blocks execution of system commands
- ✅ Permits legitimate MCP server runtimes
- ✅ Easy to extend for new runtimes
- ✅ Simple to understand and audit
- ❌ Requires updates to add new runtimes

### Why No Shell Execution?

MCP servers are executed directly without a shell:

- ✅ Prevents shell metacharacter interpretation
- ✅ Faster execution (no shell overhead)
- ✅ More secure by default
- ✅ Better error messages
- ❌ Can't use shell features (but that's the point!)

### Why Two Layers?

Defense in depth provides redundancy:

- If allowlist has a bug, validation catches it
- If validation is bypassed somehow, allowlist blocks dangerous commands
- Both are simple and auditable
- Together they provide strong protection

## Related Documentation

- **Kubernetes Security**: `k8s-mcp-security.yaml` - Production-ready K8s configuration
- **MCP Server Import/Export**: See API documentation for `.mcp.json` format
- **Environment Variables**: See `.env.example` for secret management

## Future Enhancements

- [ ] Admin-only flag for stdio MCP server creation
- [ ] Per-server resource limits (CPU, memory, network)
- [ ] Audit logging for all MCP server operations
- [x] Configurable allowlist via environment variables ✅
- [ ] Rate limiting for MCP server creation
- [ ] Automatic runtime version detection and validation
- [ ] UI for managing allowed commands and dangerous characters

## References

- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Python subprocess Security](https://docs.python.org/3/library/subprocess.html#security-considerations)
