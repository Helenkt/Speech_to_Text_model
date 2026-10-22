"""Audit-only routes on the existing isolated, fake-microphone fixture."""
from tools.recovery_smoke_server import app, settings
from app.services.evaluator import evaluate_answer


@app.get("/fixture/conflicted-evaluation")
async def conflicted_evaluation():
    point = "A class is a blueprint"
    question = {"language": "en", "question": "What is a class?",
                "reference_answer": point, "key_points": [point]}
    return await evaluate_answer(settings, question, "A class is a blueprint. A class is not a blueprint.")
