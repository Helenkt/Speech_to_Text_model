from packaging.requirements import Requirement


def requirements(project_root, name):
    return [Requirement(line.strip()) for line in (project_root / name).read_text().splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "-"))]


def test_runtime_requirements_are_pinned_and_exclude_training_and_cli_extras(project_root):
    packages = requirements(project_root, "requirements.txt")
    by_name = {item.name: item for item in packages}
    assert len(by_name) == len(packages)
    assert {"fastapi", "uvicorn", "faster-whisper", "ctranslate2", "huggingface-hub",
            "av", "onnxruntime", "onnx", "tokenizers"} <= set(by_name)
    assert not {"torch", "transformers", "pytest", "httpx2", "ollama"} & set(by_name)
    assert by_name["fastapi"].extras == set()
    assert all(len(list(item.specifier)) == 1 and next(iter(item.specifier)).operator == "=="
               for item in packages)


def test_developer_dependencies_include_runtime_but_training_stays_separate(project_root):
    lines = (project_root / "requirements-dev.txt").read_text().splitlines()
    assert "-r requirements.txt" in lines
    assert {item.name for item in requirements(project_root, "requirements-dev.txt")} == {"pytest", "httpx2"}
    training = (project_root / "requirements-training.txt").read_text()
    assert "-r requirements.txt" not in training
    assert "torch" in training and "transformers" in training
