"""Pre-built service templates for common enterprise API integrations.

Each template provides sensible defaults that can be used to quickly
configure a new API endpoint for a well-known service.
"""

from typing import Any, Dict, List

SERVICE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "servicenow": {
        "name": "ServiceNow",
        "service_type": "servicenow",
        "description": "ServiceNow REST Table API",
        "url_template": "https://{instance}.service-now.com/api/now/table/{table_name}",
        "method": "GET",
        "headers": {
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        "auth_type": "basic",
        "timeout_seconds": 30,
        "max_retries": 3,
        "response_format": "json",
        "extract_path": "result",
        "parameter_schema": {
            "instance": {
                "type": "string",
                "required": True,
                "description": "ServiceNow instance name (e.g. dev12345)",
            },
            "table_name": {
                "type": "string",
                "required": True,
                "description": "Table name (e.g. incident, sys_user, change_request)",
            },
        },
    },
    "salesforce": {
        "name": "Salesforce",
        "service_type": "salesforce",
        "description": "Salesforce REST API",
        "url_template": "https://{instance}.salesforce.com/services/data/v{api_version}/{resource}",
        "method": "GET",
        "headers": {
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        "auth_type": "bearer",
        "timeout_seconds": 30,
        "max_retries": 3,
        "response_format": "json",
        "parameter_schema": {
            "instance": {
                "type": "string",
                "required": True,
                "description": "Salesforce instance name (e.g. na1, eu5)",
            },
            "api_version": {
                "type": "string",
                "required": True,
                "description": "API version number (e.g. 59.0)",
                "default": "59.0",
            },
            "resource": {
                "type": "string",
                "required": True,
                "description": "REST resource path (e.g. sobjects/Account)",
            },
        },
    },
    "workday": {
        "name": "Workday",
        "service_type": "workday",
        "description": "Workday REST API",
        "url_template": "https://{host}/ccx/api/{api_version}/{tenant}/{resource}",
        "method": "GET",
        "headers": {
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        "auth_type": "bearer",
        "timeout_seconds": 60,
        "max_retries": 3,
        "response_format": "json",
        "parameter_schema": {
            "host": {
                "type": "string",
                "required": True,
                "description": "Workday host (e.g. wd5-impl-services1.workday.com)",
            },
            "api_version": {
                "type": "string",
                "required": True,
                "description": "API version (e.g. v1, v2)",
                "default": "v1",
            },
            "tenant": {
                "type": "string",
                "required": True,
                "description": "Workday tenant name",
            },
            "resource": {
                "type": "string",
                "required": True,
                "description": "REST resource path (e.g. workers, organizations)",
            },
        },
    },
    "azure": {
        "name": "Azure Management API",
        "service_type": "azure",
        "description": "Azure Resource Manager REST API",
        "url_template": "https://management.azure.com/subscriptions/{subscription_id}/{resource_path}?api-version={api_version}",
        "method": "GET",
        "headers": {
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        "auth_type": "bearer",
        "timeout_seconds": 30,
        "max_retries": 3,
        "response_format": "json",
        "extract_path": "value",
        "parameter_schema": {
            "subscription_id": {
                "type": "string",
                "required": True,
                "description": "Azure subscription ID",
            },
            "resource_path": {
                "type": "string",
                "required": True,
                "description": "Resource path (e.g. resourceGroups, providers/Microsoft.Compute/virtualMachines)",
            },
            "api_version": {
                "type": "string",
                "required": True,
                "description": "API version (e.g. 2023-07-01)",
            },
        },
    },
    "aws": {
        "name": "AWS API",
        "service_type": "aws",
        "description": "AWS Service API",
        "url_template": "https://{service}.{region}.amazonaws.com/{path}",
        "method": "GET",
        "headers": {
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        "auth_type": "api_key",
        "timeout_seconds": 30,
        "max_retries": 3,
        "response_format": "json",
        "parameter_schema": {
            "service": {
                "type": "string",
                "required": True,
                "description": "AWS service name (e.g. s3, dynamodb, lambda)",
            },
            "region": {
                "type": "string",
                "required": True,
                "description": "AWS region (e.g. us-east-1, eu-west-1)",
            },
            "path": {
                "type": "string",
                "required": False,
                "description": "API path",
                "default": "",
            },
        },
    },
    "gcp": {
        "name": "Google Cloud API",
        "service_type": "gcp",
        "description": "Google Cloud Platform REST API",
        "url_template": "https://{service}.googleapis.com/{api_version}/{resource}",
        "method": "GET",
        "headers": {
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        "auth_type": "bearer",
        "timeout_seconds": 30,
        "max_retries": 3,
        "response_format": "json",
        "parameter_schema": {
            "service": {
                "type": "string",
                "required": True,
                "description": "GCP service (e.g. compute, storage, bigquery)",
            },
            "api_version": {
                "type": "string",
                "required": True,
                "description": "API version (e.g. v1, v2)",
                "default": "v1",
            },
            "resource": {
                "type": "string",
                "required": True,
                "description": "Resource path (e.g. projects/{project}/zones/{zone}/instances)",
            },
        },
    },
}


def get_templates() -> List[Dict[str, Any]]:
    """Return all service templates as a list with IDs."""
    return [{"id": key, **value} for key, value in SERVICE_TEMPLATES.items()]


def get_template(template_id: str) -> Dict[str, Any] | None:
    """Return a specific template by ID."""
    template = SERVICE_TEMPLATES.get(template_id)
    if template:
        return {"id": template_id, **template}
    return None
