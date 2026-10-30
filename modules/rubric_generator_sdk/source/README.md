# Rubric Generator SDK

Version 1.0.0 packages the existing Rubric Generator V15 (1.5.0-task-source-scope)
and core 1.3.0 under an isolated Python namespace. Input: a question and a reference
answer. Output: a draft rubric with source evidence, question types and integer
point allocations. This package does not grade candidate answers or train model
weights. Ollama with qwen3:4b-instruct-2507-q4_K_M is a separate local dependency.

Public entry points: RubricGenerator.generate, RubricGenerator.generate_input,
validate_rubric_dict, and python -m rubric_generator_sdk.
Read README_VI.md and INTEGRATION.md in the release ZIP for Windows installation,
process isolation, error handling and draft review.
