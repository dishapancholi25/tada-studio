"""Configuration utilities for HTTP request tool."""

import re
from typing import Any, Dict

from pydantic import BaseModel, Field, create_model

from .schemas import HttpRequestConfig


class ToolDescriptionBuilder:
    """Builder for creating tool descriptions based on configuration."""

    @staticmethod
    def build_description(config: HttpRequestConfig) -> str:
        """Build a dynamic tool description based on configuration.

        Args:
            config: HTTP request configuration

        Returns:
            Formatted tool description string
        """
        description_parts = [f"Make {config.method} request to {config.url_template}"]

        if config.parameter_schema:
            description_parts.append("\n\nParameters (provide as JSON object):")
            for param_name, param_def in config.parameter_schema.items():
                # Handle both dict and object parameter definitions
                if isinstance(param_def, dict):
                    param_type = param_def.get("param_type", "string")
                    param_desc = param_def.get("description", "")
                    is_required = param_def.get("required", False)
                    location_hint = param_def.get("location", "query")
                    param_example = param_def.get("example", "")
                else:
                    # It's a ParameterDefinition object
                    param_type = getattr(param_def, "param_type", "string")
                    param_desc = getattr(param_def, "description", "")
                    is_required = getattr(param_def, "required", False)
                    location_hint = getattr(param_def, "location", "query")
                    param_example = getattr(param_def, "example", "")

                req_marker = " (required)" if is_required else " (optional)"
                loc_marker = f" [{location_hint}]"
                example_text = f" e.g., {param_example}" if param_example else ""
                description_parts.append(
                    f"- {param_name}: {param_type}{req_marker}{loc_marker} - {param_desc}{example_text}"
                )
        else:
            # Fallback to old behavior for backward compatibility
            url_params = re.findall(r"\{(\w+)\}", config.url_template)
            body_placeholders = (
                re.findall(r"\{(\w+)\}", config.request_body_template)
                if config.request_body_template
                else []
            )
            all_params = list(set(url_params + body_placeholders))

            if len(all_params) == 0:
                description_parts.append("No parameters required.")
            elif len(all_params) == 1:
                single_param_name = all_params[0]
                description_parts.append(
                    f"Pass the {single_param_name} value directly."
                )
            else:
                param_desc = ", ".join(all_params)
                description_parts.append(
                    f"Pass parameters as JSON with fields: {param_desc}"
                )

        return "\n".join(description_parts)


class ArgsSchemaBuilder:
    """Builder for creating dynamic Pydantic argument schemas."""

    @staticmethod
    def build_args_schema(
        parameter_schema: Dict[str, Any], url_template: str = ""
    ) -> type[BaseModel]:
        """Build dynamic Pydantic model based on parameter schema.

        When parameter_schema is empty but url_template contains path parameters,
        auto-generates schema fields for those path parameters.

        Args:
            parameter_schema: Dictionary of parameter definitions
            url_template: URL template that may contain {placeholder} path parameters

        Returns:
            Pydantic model class
        """
        from typing import Optional

        field_definitions = {}

        for param_name, param_def in parameter_schema.items():
            # Extract parameter details
            if isinstance(param_def, dict):
                param_type_str = param_def.get("param_type", "string")
                param_desc = param_def.get("description", f"{param_name} parameter")
                param_required = param_def.get("required", False)
                param_default = param_def.get("default_value", None)
            else:
                param_type_str = getattr(param_def, "param_type", "string")
                param_desc = getattr(
                    param_def, "description", f"{param_name} parameter"
                )
                param_required = getattr(param_def, "required", False)
                param_default = getattr(param_def, "default_value", None)

            # Map parameter types to Python types
            field_type = ArgsSchemaBuilder._map_param_type(param_type_str)

            # Create field with proper optionality
            if param_required:
                field_definitions[param_name] = (
                    field_type,
                    Field(description=param_desc),
                )
            else:
                field_definitions[param_name] = (
                    Optional[field_type],
                    Field(default=param_default, description=param_desc),
                )

        # Create the dynamic model or use a default if no parameters
        if field_definitions:
            return create_model("HttpRequestArgs", **field_definitions)

        # No explicit parameter_schema - try to auto-generate from URL path parameters
        if url_template:
            path_params = re.findall(r"\{(\w+)\}", url_template)
            if path_params:
                for param_name in path_params:
                    field_definitions[param_name] = (
                        str,
                        Field(
                            description=f"Value for {{{param_name}}} in the URL path"
                        ),
                    )
                return create_model("HttpRequestArgs", **field_definitions)

        # Final fallback - generic parameters field for backward compatibility
        class DefaultHttpRequestArgs(BaseModel):
            parameters: Optional[str] = Field(
                default="", description="Parameters as JSON string"
            )

        return DefaultHttpRequestArgs

    @staticmethod
    def _map_param_type(param_type_str: str) -> type:
        """Map parameter type string to Python type.

        Args:
            param_type_str: Type string (number, integer, boolean, array, object, string)

        Returns:
            Python type
        """
        type_mapping = {
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "string": str,
        }
        return type_mapping.get(param_type_str, str)


class ConfigValidator:
    """Validator for HTTP request configuration."""

    @staticmethod
    def validate(config: HttpRequestConfig) -> tuple[bool, list[str], list[str]]:
        """Validate HTTP request configuration.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # Validate HTTP method
        valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
        if config.method.upper() not in valid_methods:
            errors.append(
                f"Invalid HTTP method: {config.method}. "
                f"Must be one of {', '.join(valid_methods)}"
            )

        # Validate URL template
        if not config.url_template:
            errors.append("URL template is required")
        elif not config.url_template.startswith(("http://", "https://")):
            warnings.append(
                "URL template should start with http:// or https:// for proper requests"
            )

        # Validate timeout
        if config.timeout_seconds < 1 or config.timeout_seconds > 300:
            warnings.append("timeout_seconds should be between 1 and 300 seconds")

        # Validate retries
        if config.max_retries < 0 or config.max_retries > 10:
            warnings.append("max_retries should be between 0 and 10")

        # Validate response format
        valid_formats = ["auto", "json", "xml", "binary"]
        if config.response_format not in valid_formats:
            errors.append(
                f"Invalid response_format: {config.response_format}. "
                f"Must be one of {', '.join(valid_formats)}"
            )

        # Validate error handling
        valid_error_handling = ["fail", "retry", "continue"]
        if config.error_handling not in valid_error_handling:
            errors.append(
                f"Invalid error_handling: {config.error_handling}. "
                f"Must be one of {', '.join(valid_error_handling)}"
            )

        is_valid = len(errors) == 0
        return is_valid, errors, warnings
