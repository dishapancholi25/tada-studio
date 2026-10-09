"""Declarative filter template definitions.

Each template defines a reusable filter pattern with configurable parameters.
Templates are referenced by ID in the CustomFilter.template_id field.
"""

FILTER_TEMPLATES = {
    # NOTE: "pii_detector" and "toxicity_check" have been removed.
    # PII detection is now a first-class LLM Guard scanner (anonymize_pii).
    # Toxicity detection is now a first-class LLM Guard scanner (detect_toxicity).
    # Legacy policies referencing these template IDs are handled with deprecation
    # warnings in the declarative executor.
    "topic_guard": {
        "name": "Topic Guard",
        "description": "Restricts content to allowed topics or blocks forbidden topics",
        "params": {
            "mode": {
                "type": "enum",
                "default": "blocklist",
                "options": ["allowlist", "blocklist"],
            },
            "topics": {
                "type": "list",
                "default": [],
            },
        },
    },
    "language_detector": {
        "name": "Language Detector",
        "description": "Ensures content is in allowed languages",
        "params": {
            "allowed_languages": {
                "type": "list",
                "default": ["en"],
                "options": [
                    "en",
                    "es",
                    "fr",
                    "de",
                    "it",
                    "pt",
                    "zh",
                    "ja",
                    "ko",
                    "ar",
                    "hi",
                    "ru",
                ],
            },
        },
    },
    "word_count_limit": {
        "name": "Word Count Limit",
        "description": "Limits content to a maximum word count",
        "params": {
            "max_words": {
                "type": "int",
                "default": 500,
                "min": 1,
                "max": 100000,
            },
        },
    },
}
