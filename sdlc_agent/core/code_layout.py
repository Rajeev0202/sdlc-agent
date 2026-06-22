"""
Code Layout Configuration

Defines the folder structure and file naming patterns for generated code.
Customize this file to match your organization's standards.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class LayoutStyle(Enum):
    """Predefined layout styles."""
    FLAT = "flat"                    # src/us_001.py
    BY_DOMAIN = "by_domain"          # src/payments/us_001.py
    BY_FEATURE = "by_feature"        # src/features/card_freeze/us_001.py
    BY_PERSONA = "by_persona"        # src/customer/us_001.py
    BY_LAYER = "by_layer"            # src/api/us_001.py, src/ui/us_002.py
    FEATURE_MODULES = "feature_modules"  # src/card_freeze/service.py, src/card_freeze/api.py
    CONTROLLER_SERVICE = "controller_service"  # src/controllers/card_controller.py, src/services/card_service.py


@dataclass
class CodeLayoutConfig:
    """Configuration for code file layout."""

    # Style preset or custom function
    style: LayoutStyle | Callable = LayoutStyle.FLAT

    # Base directories
    src_dir: str = "src"
    test_dir: str = "tests"

    # File naming patterns
    impl_pattern: str = "{module_name}.py"           # Implementation file
    test_pattern: str = "test_{module_name}.py"      # Test file

    # Module name transformation
    # Options: "snake_case" (us_001), "kebab-case" (us-001), "camelCase", "PascalCase"
    module_case: str = "snake_case"

    # Controller-Service architecture settings
    # When style=CONTROLLER_SERVICE, determines which layer this story belongs to
    # Options: "controller", "service", "model", "repository", "both" (controller+service)
    default_layer: str = "both"  # Generate both controller and service for each story

    # Whether to group by story type (US, BUG, TASK)
    group_by_type: bool = False

    # Custom domain mapping (story ID prefix -> domain folder)
    domain_mapping: dict[str, str] | None = None

    # Feature name extraction (from story.want)
    extract_feature_from_want: bool = True


# Global configuration - modify this to change layout
LAYOUT_CONFIG = CodeLayoutConfig(
    style=LayoutStyle.FLAT,  # Change this to customize
    src_dir="src",
    test_dir="tests",
    module_case="snake_case",
    group_by_type=False,
)


def get_layout_config() -> CodeLayoutConfig:
    """Get the active layout configuration."""
    # Allow environment override
    style_env = os.getenv("CODE_LAYOUT_STYLE")
    if style_env:
        try:
            LAYOUT_CONFIG.style = LayoutStyle(style_env)
        except ValueError:
            pass

    return LAYOUT_CONFIG


def _slugify(text: str, case: str = "snake_case") -> str:
    """Convert text to a valid identifier."""
    # Remove special chars, convert to lowercase
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")

    if case == "snake_case":
        return slug
    elif case == "kebab-case":
        return slug.replace("_", "-")
    elif case == "camelCase":
        parts = slug.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])
    elif case == "PascalCase":
        return "".join(p.capitalize() for p in slug.split("_"))

    return slug


def _extract_feature_name(story_want: str) -> str:
    """Extract a short feature name from story 'want' clause."""
    # Common patterns to extract: "freeze card", "view balance", "transfer funds"
    want_lower = story_want.lower()

    # Remove common prefixes
    for prefix in ["to ", "be able to ", "have the ability to "]:
        if want_lower.startswith(prefix):
            want_lower = want_lower[len(prefix):]

    # Take first 2-3 words as feature name
    words = want_lower.split()[:3]
    feature = "_".join(words)

    return _slugify(feature)


def _extract_entity_name(story_want: str) -> str:
    """
    Extract the primary entity/resource name from story 'want' clause.

    Examples:
    - "freeze my card" -> "card"
    - "view account balance" -> "account"
    - "transfer funds" -> "transfer"
    - "create payment" -> "payment"
    """
    want_lower = story_want.lower()

    # Remove common prefixes
    for prefix in ["to ", "be able to ", "have the ability to ", "my ", "the "]:
        want_lower = want_lower.replace(prefix, " ")

    # Common entity keywords (noun extraction)
    entity_keywords = {
        "card": "card",
        "account": "account",
        "balance": "balance",
        "payment": "payment",
        "transfer": "transfer",
        "transaction": "transaction",
        "user": "user",
        "customer": "customer",
        "profile": "profile",
        "notification": "notification",
        "report": "report",
        "statement": "statement",
        "loan": "loan",
        "credit": "credit",
        "debit": "debit",
        "beneficiary": "beneficiary",
    }

    # Find first matching entity keyword
    words = want_lower.split()
    for word in words:
        cleaned = word.strip(",.!?;:")
        if cleaned in entity_keywords:
            return entity_keywords[cleaned]

    # Fallback: use the last noun-like word (usually the object)
    if len(words) >= 2:
        return _slugify(words[-1])

    return _slugify(want_lower.split()[0] if words else "feature")


def _infer_architectural_layer(story) -> str:
    """
    Infer the architectural layer (controller, service, model, repository) for a story.

    Returns:
        "controller", "service", "model", or "repository"
    """
    want_lower = story.want.lower()

    # API/Controller layer indicators
    controller_keywords = ["endpoint", "api", "route", "request", "response", "validate input"]
    if any(k in want_lower for k in controller_keywords):
        return "controller"

    # Repository/Data layer indicators
    repository_keywords = ["database", "persist", "store", "retrieve", "query", "save", "delete from db"]
    if any(k in want_lower for k in repository_keywords):
        return "repository"

    # Model/Domain layer indicators
    model_keywords = ["define", "schema", "model", "entity", "structure"]
    if any(k in want_lower for k in model_keywords):
        return "model"

    # Default to service layer (business logic)
    return "service"


def get_implementation_path(story, config: CodeLayoutConfig | None = None) -> str:
    """
    Get the file path for a story's implementation.

    Args:
        story: UserStory object with id, persona, want, etc.
        config: Layout configuration (uses global if None)

    Returns:
        Relative file path like "src/payments/card_freeze.py"

    Examples:
        FLAT: src/us_001.py
        BY_DOMAIN: src/payments/us_001.py
        BY_FEATURE: src/features/card_freeze/implementation.py
        BY_PERSONA: src/customer/us_001.py
        FEATURE_MODULES: src/card_freeze/service.py
    """
    config = config or get_layout_config()

    # Base module name from story ID
    module_name = story.id.lower().replace("-", "_")

    # Apply case transformation
    module_name = _slugify(module_name, config.module_case)

    # Determine folder structure based on style
    if callable(config.style):
        # Custom function
        folder_path = config.style(story)
    elif config.style == LayoutStyle.FLAT:
        # src/us_001.py
        folder_path = ""

    elif config.style == LayoutStyle.BY_DOMAIN:
        # src/payments/us_001.py
        domain = _infer_domain(story, config)
        folder_path = domain

    elif config.style == LayoutStyle.BY_FEATURE:
        # src/features/card_freeze/us_001.py
        feature = _extract_feature_name(story.want) if config.extract_feature_from_want else module_name
        folder_path = f"features/{feature}"

    elif config.style == LayoutStyle.BY_PERSONA:
        # src/customer/us_001.py
        persona_slug = _slugify(story.persona)
        folder_path = persona_slug

    elif config.style == LayoutStyle.BY_LAYER:
        # src/api/us_001.py or src/ui/us_002.py
        layer = _infer_layer(story)
        folder_path = layer

    elif config.style == LayoutStyle.FEATURE_MODULES:
        # src/card_freeze/service.py
        feature = _extract_feature_name(story.want) if config.extract_feature_from_want else module_name
        folder_path = feature
        module_name = "service"  # Standard name

    elif config.style == LayoutStyle.CONTROLLER_SERVICE:
        # src/controllers/card_controller.py or src/services/card_service.py
        # Extract entity name from story (e.g., "freeze card" -> "card")
        entity = _extract_entity_name(story.want)

        # Determine layer based on story context
        layer = _infer_architectural_layer(story)

        if config.default_layer == "both":
            # Generate service file (we'll handle controller separately in build_skill)
            folder_path = "services"
            module_name = f"{entity}_service"
        else:
            folder_path = f"{layer}s"  # "controllers", "services", "models", "repositories"
            module_name = f"{entity}_{layer}"

    else:
        folder_path = ""

    # Optionally group by story type (US, BUG, TASK)
    if config.group_by_type:
        story_type = story.id.split("-")[0].lower() if "-" in story.id else "story"
        folder_path = f"{story_type}/{folder_path}".rstrip("/")

    # Build full path
    filename = config.impl_pattern.format(module_name=module_name)

    if folder_path:
        full_path = f"{config.src_dir}/{folder_path}/{filename}"
    else:
        full_path = f"{config.src_dir}/{filename}"

    return full_path.replace("//", "/")


def get_test_path(story, config: CodeLayoutConfig | None = None) -> str:
    """
    Get the file path for a story's test file.

    Mirrors the implementation structure but in test directory.
    """
    config = config or get_layout_config()

    # Get implementation path and mirror it in test directory
    impl_path = get_implementation_path(story, config)

    # Replace src with test directory
    test_path = impl_path.replace(config.src_dir, config.test_dir, 1)

    # Apply test naming pattern
    module_name = story.id.lower().replace("-", "_")
    module_name = _slugify(module_name, config.module_case)

    # Replace filename with test pattern
    impl_filename = config.impl_pattern.format(module_name=module_name)
    test_filename = config.test_pattern.format(module_name=module_name)

    test_path = test_path.replace(impl_filename, test_filename)

    return test_path


def get_controller_path(story, config: CodeLayoutConfig | None = None) -> str:
    """
    Get the controller file path for Controller-Service architecture.

    Only relevant when style=CONTROLLER_SERVICE and default_layer="both".

    Returns:
        Path like "src/controllers/card_controller.py"
    """
    config = config or get_layout_config()

    if config.style != LayoutStyle.CONTROLLER_SERVICE:
        return None

    entity = _extract_entity_name(story.want)
    module_name = f"{entity}_controller"

    filename = config.impl_pattern.format(module_name=module_name)
    return f"{config.src_dir}/controllers/{filename}"


def get_service_path(story, config: CodeLayoutConfig | None = None) -> str:
    """
    Get the service file path for Controller-Service architecture.

    Returns:
        Path like "src/services/card_service.py"
    """
    config = config or get_layout_config()

    if config.style != LayoutStyle.CONTROLLER_SERVICE:
        return None

    entity = _extract_entity_name(story.want)
    module_name = f"{entity}_service"

    filename = config.impl_pattern.format(module_name=module_name)
    return f"{config.src_dir}/services/{filename}"


def _infer_domain(story, config: CodeLayoutConfig) -> str:
    """Infer domain from story context."""
    # Use custom mapping if provided
    if config.domain_mapping:
        story_prefix = story.id.split("-")[0] if "-" in story.id else ""
        if story_prefix in config.domain_mapping:
            return config.domain_mapping[story_prefix]

    # Keyword-based inference
    want_lower = story.want.lower()

    if any(k in want_lower for k in ["payment", "transfer", "pay", "transaction"]):
        return "payments"
    elif any(k in want_lower for k in ["card", "freeze", "unfreeze", "block"]):
        return "cards"
    elif any(k in want_lower for k in ["auth", "login", "sso", "sign in"]):
        return "auth"
    elif any(k in want_lower for k in ["balance", "account", "statement"]):
        return "accounts"
    elif any(k in want_lower for k in ["report", "audit", "compliance"]):
        return "compliance"
    elif any(k in want_lower for k in ["notification", "alert", "email", "sms"]):
        return "notifications"

    return "core"


def _infer_layer(story) -> str:
    """Infer application layer from story context."""
    want_lower = story.want.lower()

    if any(k in want_lower for k in ["api", "endpoint", "service", "backend"]):
        return "api"
    elif any(k in want_lower for k in ["ui", "screen", "page", "view", "frontend", "display"]):
        return "ui"
    elif any(k in want_lower for k in ["database", "schema", "migration", "model"]):
        return "data"
    elif any(k in want_lower for k in ["workflow", "process", "automation"]):
        return "workflows"

    return "core"


def create_directories_for_story(story, config: CodeLayoutConfig | None = None) -> list[str]:
    """
    Create all necessary directories for a story.

    Returns:
        List of directory paths created
    """
    from pathlib import Path

    config = config or get_layout_config()

    impl_path = get_implementation_path(story, config)
    test_path = get_test_path(story, config)

    directories = []

    for file_path in [impl_path, test_path]:
        dir_path = Path(file_path).parent
        if dir_path != Path("."):
            dir_path.mkdir(parents=True, exist_ok=True)
            directories.append(str(dir_path))

    return list(set(directories))


# Quick configuration presets
def configure_flat_layout():
    """Flat structure: src/us_001.py, tests/test_us_001.py"""
    LAYOUT_CONFIG.style = LayoutStyle.FLAT


def configure_domain_layout(domain_mapping: dict[str, str] | None = None):
    """Domain-based: src/payments/us_001.py"""
    LAYOUT_CONFIG.style = LayoutStyle.BY_DOMAIN
    if domain_mapping:
        LAYOUT_CONFIG.domain_mapping = domain_mapping


def configure_feature_layout():
    """Feature-based: src/features/card_freeze/us_001.py"""
    LAYOUT_CONFIG.style = LayoutStyle.BY_FEATURE
    LAYOUT_CONFIG.extract_feature_from_want = True


def configure_layer_layout():
    """Layer-based: src/api/us_001.py, src/ui/us_002.py"""
    LAYOUT_CONFIG.style = LayoutStyle.BY_LAYER


def configure_feature_modules():
    """Feature modules: src/card_freeze/service.py, src/card_freeze/api.py"""
    LAYOUT_CONFIG.style = LayoutStyle.FEATURE_MODULES
    LAYOUT_CONFIG.extract_feature_from_want = True


def configure_controller_service_layout(generate_both: bool = True):
    """
    Controller-Service architecture:
    - src/controllers/card_controller.py
    - src/services/card_service.py
    - tests/controllers/test_card_controller.py
    - tests/services/test_card_service.py

    Args:
        generate_both: If True, generates both controller and service for each story.
                      If False, infers layer from story context.
    """
    LAYOUT_CONFIG.style = LayoutStyle.CONTROLLER_SERVICE
    LAYOUT_CONFIG.default_layer = "both" if generate_both else "service"
