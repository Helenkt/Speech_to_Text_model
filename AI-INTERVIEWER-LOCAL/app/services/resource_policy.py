"""Shared CPU and model residency budgets; never change grading thresholds."""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ResourcePolicy:
    memory_class: str
    staged: bool
    cpu_threads: int
    llm_batch_size: int
    retire_worker_between_stages: bool

    def snapshot(self):
        return asdict(self)


def resolve_resource_policy(total_memory_gb: float, available_memory_gb: float,
                            cpu_threads: int) -> ResourcePolicy:
    # Physical memory may be slightly below the advertised 4/8 GB capacity.
    if total_memory_gb <= 0:
        memory_class = "unknown"
    elif total_memory_gb <= 4.5:
        memory_class = "4gb"
    elif total_memory_gb <= 8.5:
        memory_class = "8gb"
    else:
        memory_class = "standard"
    staged = memory_class != "standard" or available_memory_gb < 4
    limited = memory_class in {"4gb", "unknown"}
    threads = max(1, min(2 if limited else 4, max(1, cpu_threads) // 2))
    return ResourcePolicy(memory_class, staged, threads, 64 if limited else 128,
                          limited)


def detect_resource_policy() -> ResourcePolicy:
    # Memory checks on each stage must not probe CUDA or launch nvidia-smi.
    from app.services.speech_to_text import _memory_stats_gb

    total, available, _ = _memory_stats_gb()
    return resolve_resource_policy(total, available, os.cpu_count() or 1)


def canonical_ollama_name(name: str) -> str:
    # Registry ports are not tags; Ollama adds :latest to an untagged model.
    return name if ":" in name.rsplit("/", 1)[-1] else name + ":latest"


def ollama_request_resources(settings) -> dict:
    policy = detect_resource_policy()
    keep_alive = settings.ollama_keep_alive
    options = {"num_thread": policy.cpu_threads}
    if policy.staged:
        # Preserve the context/output budgets; smaller batches reduce scratch RAM.
        options["num_batch"] = policy.llm_batch_size
        limit = 30 if policy.retire_worker_between_stages else 120
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(ms|s|m|h)?\s*", str(keep_alive))
        seconds = (float(match[1]) * {None: 1, "ms": .001, "s": 1, "m": 60, "h": 3600}[match[2]]) if match else float("inf")
        if seconds > limit:
            keep_alive = "30s" if limit == 30 else "2m"
    return {"keep_alive": keep_alive, "options": options}
