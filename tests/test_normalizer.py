"""Unit tests for L3 skill normalizer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.l3_normalize.normalizer import normalize_skill, normalize_skills


def test_alias_resolution():
    assert normalize_skill("JS") == "javascript"
    assert normalize_skill("k8s") == "kubernetes"
    assert normalize_skill("ts") == "typescript"
    assert normalize_skill("react.js") == "react"
    assert normalize_skill("node.js") == "nodejs"
    assert normalize_skill("postgres") == "postgresql"
    assert normalize_skill("ml") == "machine_learning"
    assert normalize_skill("dl") == "deep_learning"
    print("PASS: alias resolution")


def test_direct_node():
    assert normalize_skill("python") == "python"
    assert normalize_skill("docker") == "docker"
    assert normalize_skill("kubernetes") == "kubernetes"
    assert normalize_skill("tensorflow") == "tensorflow"
    print("PASS: direct node lookup")


def test_case_insensitive():
    assert normalize_skill("TensorFlow") == "tensorflow"
    assert normalize_skill("PYTHON") == "python"
    assert normalize_skill("React") == "react"
    print("PASS: case insensitive")


def test_underscore_variant():
    assert normalize_skill("machine learning") == "machine_learning"
    assert normalize_skill("deep learning") == "deep_learning"
    assert normalize_skill("natural language processing") == "natural_language_processing"
    print("PASS: underscore variant")


def test_list_normalization():
    result = normalize_skills(["JS", "k8s", "TensorFlow", "react.js", "Python"])
    assert "javascript" in result
    assert "kubernetes" in result
    assert "tensorflow" in result
    assert "react" in result
    assert "python" in result
    print(f"PASS: list normalization -> {result}")


if __name__ == "__main__":
    test_alias_resolution()
    test_direct_node()
    test_case_insensitive()
    test_underscore_variant()
    test_list_normalization()
    print("\nAll normalizer tests passed.")
