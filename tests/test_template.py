"""Unit tests for template loading."""

from __future__ import annotations

import pytest

from labctl.template import (
    TemplateNotFoundError,
    list_templates,
    load_template,
)


class TestLoadTemplate:
    def test_load_blank_template(self):
        tpl = load_template("blank")
        assert tpl.name == "blank"
        assert tpl.dockerfile.exists()
        assert tpl.ports == []
        assert tpl.volumes == []

    def test_load_unknown_raises(self):
        with pytest.raises(TemplateNotFoundError, match="not found"):
            load_template("nonexistent-template-xyz")

    def test_error_lists_available(self):
        with pytest.raises(TemplateNotFoundError) as exc_info:
            load_template("nonexistent-template-xyz")
        assert "blank" in exc_info.value.available

    def test_image_tag(self):
        tpl = load_template("blank")
        assert tpl.image_tag == "labctl-tpl-blank:latest"


class TestListTemplates:
    def test_includes_blank(self):
        templates = list_templates()
        names = [t.name for t in templates]
        assert "blank" in names

    def test_returns_template_objects(self):
        templates = list_templates()
        for tpl in templates:
            assert tpl.name
            assert tpl.path.exists()
