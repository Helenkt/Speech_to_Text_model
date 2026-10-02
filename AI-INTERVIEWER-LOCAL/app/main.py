from __future__ import annotations

import functools
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.database import (
    active_question_count,
    active_user_count,
    init_database,
    total_user_count,
)
from app.schemas import (
    AccountActiveRequest,
    ExamRoundCreateRequest,
    ExamStatusRequest,
    LoginRequest,
    StartInterviewRequest,
    SubmitAnswerRequest,
)
from app.services.account_importer import (
    AccountImportError,
    import_accounts,
    list_accounts,
    seed_demo_accounts,
    set_account_active,
)
from app.services.auth import (
    COOKIE_NAME,
    AuthError,
    authenticate,
    create_session,
    get_user_by_token,
    revoke_session,
)
from app.services.evaluator import ollama_status
from app.services.transcript_corrector import correct_transcript
from app.services.exam_service import (
    ExamError,
    create_exam_round,
    delete_exam_round,
    find_candidate_exam,
    list_exam_attempts,
    list_exam_rounds,
    set_exam_status,
    start_real_interview,
)
from app.services.interview_engine import (
    InterviewError,
    delete_practice_history,
    delete_real_interview_result,
    finish_interview,
    interview_report,
    list_practice_history,
    question_summary,
    session_metadata,
    start_interview,
    submit_answer,
)
from app.services.question_importer import (
    QuestionBankError,
    import_question_bank,
    load_demo_banks,
)
from app.services.speech_to_text import (
    assess_transcription_quality,
    SpeechToTextError,
    stt_status,
    transcribe_bytes,
)
from app.services.transcription_store import (
    TranscriptionError,
    save_transcription,
    transcription_context,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_database(app_settings.database_path)
        if app_settings.auto_seed_demo:
            if active_question_count(app_settings.database_path) == 0:
                load_demo_banks(app_settings.database_path, app_settings.demo_data_dir)
            if total_user_count(app_settings.database_path) == 0:
                seed_demo_accounts(app_settings.database_path, app_settings.demo_data_dir)
        yield

    app = FastAPI(
        title="AI Interview Local",
        version="1.6.0",
        description="Hệ thống AI Interview local với phân quyền Giáo viên và Ứng viên.",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.mount("/static", StaticFiles(directory=app_settings.static_dir), name="static")

    def current_user(request: Request) -> dict[str, Any]:
        user = get_user_by_token(
            app_settings.database_path, request.cookies.get(COOKIE_NAME)
        )
        if not user:
            raise HTTPException(status_code=401, detail="Vui lòng đăng nhập")
        return user

    def teacher_user(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if user["role"] != "teacher":
            raise HTTPException(
                status_code=403, detail="Chức năng này chỉ dành cho Giáo viên"
            )
        return user

    def candidate_user(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if user["role"] != "candidate":
            raise HTTPException(
                status_code=403, detail="Chức năng này chỉ dành cho Ứng viên"
            )
        return user

    async def read_upload(file: UploadFile) -> bytes:
        maximum = app_settings.max_upload_mb * 1024 * 1024
        content = await file.read(maximum + 1)
        if len(content) > maximum:
            raise HTTPException(
                status_code=413,
                detail=f"Tệp vượt quá giới hạn {app_settings.max_upload_mb} MB",
            )
        if not content:
            raise HTTPException(status_code=400, detail="Tệp rỗng")
        return content

    @app.get("/", include_in_schema=False)
    async def home() -> FileResponse:
        return FileResponse(app_settings.static_dir / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        ollama = await ollama_status(app_settings)
        return {
            "status": "ok",
            "database": {
                "ready": True,
                "questions": active_question_count(app_settings.database_path),
                "users": active_user_count(app_settings.database_path),
            },
            "evaluator_mode": app_settings.evaluator_mode,
            "ollama": ollama,
            "transcript_correction": {
                "mode": app_settings.transcript_correction_mode,
                "engine": f"ollama:{app_settings.ollama_model}",
                "ready": (
                    app_settings.transcript_correction_mode != "off"
                    and ollama["running"]
                    and ollama["model_available"]
                ),
                "raw_transcript_preserved": True,
            },
            "speech_to_text": stt_status(app_settings),
        }

    @app.post("/api/auth/login")
    async def login(payload: LoginRequest) -> JSONResponse:
        try:
            user = authenticate(
                app_settings.database_path, payload.username, payload.password
            )
            token, max_age = create_session(
                app_settings.database_path, user["user_id"]
            )
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        response = JSONResponse({"user": user})
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=max_age,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
        )
        return response

    @app.get("/api/auth/me")
    async def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        return {"user": user}

    @app.post("/api/auth/logout")
    async def logout(request: Request) -> JSONResponse:
        revoke_session(app_settings.database_path, request.cookies.get(COOKIE_NAME))
        response = JSONResponse({"logged_out": True})
        response.delete_cookie(COOKIE_NAME, path="/")
        return response

    @app.get("/api/questions/summary")
    async def questions_summary(
        _: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        return question_summary(app_settings.database_path)

    @app.get("/api/questions/template")
    async def question_template(
        _: dict[str, Any] = Depends(teacher_user),
    ) -> FileResponse:
        return FileResponse(
            app_settings.demo_data_dir / "question_template.json",
            media_type="application/json",
            filename="question_template.json",
        )

    @app.post("/api/questions/import")
    async def import_questions(
        file: UploadFile = File(...),
        mode: str = Form("upsert"),
        default_language: str | None = Form(None),
        _: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        content = await read_upload(file)
        try:
            return import_question_bank(
                app_settings.database_path,
                content,
                filename=file.filename or "questions.json",
                mode=mode,
                default_language=(default_language or "").strip() or None,
            )
        except QuestionBankError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/questions/reload-demo")
    async def reload_demo(
        _: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        try:
            results = await run_in_threadpool(
                load_demo_banks,
                app_settings.database_path,
                app_settings.demo_data_dir,
            )
            return {
                "imports": results,
                "summary": question_summary(app_settings.database_path),
            }
        except QuestionBankError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/teacher/accounts")
    async def accounts(
        _: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        return {"accounts": list_accounts(app_settings.database_path)}

    @app.post("/api/teacher/accounts/import")
    async def import_account_file(
        file: UploadFile = File(...),
        mode: str = Form("upsert"),
        user: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        content = await read_upload(file)
        try:
            result = import_accounts(
                app_settings.database_path,
                content,
                filename=file.filename or "accounts.csv",
                mode=mode,
                imported_by=user["user_id"],
            )
            result["accounts"] = list_accounts(app_settings.database_path)
            return result
        except AccountImportError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.patch("/api/teacher/accounts/{user_id}/active")
    async def change_account_active(
        user_id: int,
        payload: AccountActiveRequest,
        user: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        try:
            return {
                "account": set_account_active(
                    app_settings.database_path,
                    user_id,
                    active=payload.active,
                    changed_by=user["user_id"],
                )
            }
        except AccountImportError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/teacher/accounts/template/{file_format}")
    async def account_template(
        file_format: str,
        _: dict[str, Any] = Depends(teacher_user),
    ) -> FileResponse:
        if file_format not in {"xlsx", "csv", "json"}:
            raise HTTPException(status_code=404, detail="Không có định dạng mẫu này")
        path = app_settings.demo_data_dir / f"account_template.{file_format}"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Chưa tạo file mẫu")
        media_types = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
            "json": "application/json",
        }
        return FileResponse(
            path, media_type=media_types[file_format], filename=path.name
        )

    @app.post("/api/interviews/start", status_code=201)
    async def begin_practice_interview(
        payload: StartInterviewRequest,
        user: dict[str, Any] = Depends(candidate_user),
    ) -> dict[str, Any]:
        try:
            return start_interview(
                app_settings,
                user_id=user["user_id"],
                candidate_name=user["full_name"],
                language=payload.language,
                subject=payload.subject,
                question_count=payload.question_count,
                starting_difficulty=payload.starting_difficulty,
                interview_mode="practice",
                answer_mode="voice",
            )
        except InterviewError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/candidate/practice-history")
    async def candidate_practice_history(
        user: dict[str, Any] = Depends(candidate_user),
    ) -> dict[str, Any]:
        return {
            "sessions": list_practice_history(
                app_settings.database_path, user_id=user["user_id"]
            )
        }

    @app.delete("/api/candidate/practice-history/{session_id}")
    async def remove_candidate_practice_history(
        session_id: str,
        user: dict[str, Any] = Depends(candidate_user),
    ) -> dict[str, Any]:
        try:
            return delete_practice_history(
                app_settings.database_path,
                session_id=session_id,
                user_id=user["user_id"],
            )
        except InterviewError as exc:
            message = str(exc)
            status_code = 403 if "không có quyền" in message else 404
            raise HTTPException(status_code=status_code, detail=message) from exc

    @app.post("/api/interviews/{session_id}/answer")
    async def answer_question(
        session_id: str,
        payload: SubmitAnswerRequest,
        user: dict[str, Any] = Depends(candidate_user),
    ) -> dict[str, Any]:
        try:
            return await submit_answer(
                app_settings,
                session_id,
                payload.answer,
                user_id=user["user_id"],
                transcription_id=payload.transcription_id,
            )
        except InterviewError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/interviews/{session_id}/finish")
    async def end_interview(
        session_id: str,
        user: dict[str, Any] = Depends(candidate_user),
    ) -> dict[str, Any]:
        try:
            return finish_interview(
                app_settings, session_id, user_id=user["user_id"]
            )
        except InterviewError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/interviews/{session_id}/report")
    async def get_report(
        session_id: str,
        user: dict[str, Any] = Depends(current_user),
    ) -> dict[str, Any]:
        metadata = session_metadata(app_settings.database_path, session_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên phỏng vấn")
        if user["role"] != "teacher":
            if metadata["user_id"] != user["user_id"]:
                raise HTTPException(status_code=403, detail="Bạn không có quyền xem báo cáo")
            if metadata["interview_mode"] == "real":
                raise HTTPException(
                    status_code=403,
                    detail="Kết quả Interview thật chỉ hiển thị cho Giáo viên",
                )
        return interview_report(app_settings, session_id)

    @app.post("/api/teacher/exams", status_code=201)
    async def create_exam(
        payload: ExamRoundCreateRequest,
        user: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        try:
            return {
                "exam": create_exam_round(
                    app_settings.database_path,
                    created_by=user["user_id"],
                    title=payload.title,
                    exam_code=payload.exam_code,
                    language=payload.language,
                    subject=payload.subject,
                    question_count=payload.question_count,
                    starting_difficulty=payload.starting_difficulty,
                    answer_mode="voice",
                    starts_at=payload.starts_at,
                    ends_at=payload.ends_at,
                )
            }
        except ExamError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/teacher/exams")
    async def teacher_exams(
        _: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        return {"exams": list_exam_rounds(app_settings.database_path)}

    @app.delete("/api/teacher/exams/{exam_round_id}")
    async def remove_exam_round(
        exam_round_id: str,
        _: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        try:
            return delete_exam_round(app_settings.database_path, exam_round_id)
        except ExamError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch("/api/teacher/exams/{exam_round_id}/status")
    async def change_exam_status(
        exam_round_id: str,
        payload: ExamStatusRequest,
        _: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        try:
            return {
                "exam": set_exam_status(
                    app_settings.database_path, exam_round_id, payload.status
                )
            }
        except ExamError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/candidate/exams/{exam_code}")
    async def candidate_exam(
        exam_code: str,
        user: dict[str, Any] = Depends(candidate_user),
    ) -> dict[str, Any]:
        try:
            return {
                "exam": find_candidate_exam(app_settings.database_path, exam_code),
                "candidate": user,
            }
        except ExamError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/candidate/exams/{exam_code}/start", status_code=201)
    async def start_candidate_exam(
        exam_code: str,
        user: dict[str, Any] = Depends(candidate_user),
    ) -> dict[str, Any]:
        try:
            return start_real_interview(app_settings, user=user, exam_code=exam_code)
        except ExamError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/teacher/results")
    async def teacher_results(
        exam_round_id: str | None = None,
        _: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        return {
            "results": list_exam_attempts(
                app_settings.database_path, exam_round_id=exam_round_id
            )
        }

    @app.get("/api/teacher/results/{session_id}")
    async def teacher_result_detail(
        session_id: str,
        _: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        try:
            return interview_report(app_settings, session_id)
        except InterviewError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete("/api/teacher/results/{session_id}")
    async def remove_teacher_result(
        session_id: str,
        _: dict[str, Any] = Depends(teacher_user),
    ) -> dict[str, Any]:
        try:
            return delete_real_interview_result(
                app_settings.database_path, session_id=session_id
            )
        except InterviewError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/speech/transcribe")
    async def transcribe(
        file: UploadFile = File(...),
        language: str | None = Form(None),
        session_id: str | None = Form(None),
        ambient_noise_dbfs: float | None = Form(None),
        user: dict[str, Any] = Depends(candidate_user),
    ) -> dict[str, Any]:
        content = await read_upload(file)
        try:
            context = None
            if session_id:
                context = transcription_context(
                    app_settings.database_path,
                    session_id=session_id,
                    user_id=user["user_id"],
                )
            operation = functools.partial(
                transcribe_bytes,
                app_settings,
                content,
                filename=file.filename or "recording.webm",
                language=language,
                **({"hotwords": context["approved_terms"]} if context else {}),
            )
            result = await run_in_threadpool(operation)
            result = assess_transcription_quality(
                result,
                minimum_confidence=app_settings.stt_min_confidence,
                ambient_noise_dbfs=ambient_noise_dbfs,
                maximum_ambient_noise_dbfs=app_settings.stt_max_ambient_noise_dbfs,
            )
            if result.get("needs_retry") or not result["text"]:
                raise HTTPException(
                    status_code=422,
                    detail=" ".join(result.get("quality_reasons") or [
                        "Không phát hiện được giọng nói. Hãy ghi âm gần microphone và thử lại."
                    ]),
                )

            correction = await correct_transcript(
                app_settings,
                result["text"],
                language=str(result.get("language") or language or "vi"),
                approved_terms=context["approved_terms"] if context else [],
                question_text=context["question_text"] if context else "",
                uncertain_spans=result.get("uncertain_spans", []),
            ) if context else {
                "raw_text": result["text"],
                "corrected_text": result["text"],
                "correction_applied": False,
                "correction_engine": "none",
                "correction_rejected_reason": None,
                "edit_ratio": 0.0,
                "corrections": [],
                "rejected_corrections": [],
            }
            result.update(correction)
            result["text"] = correction["corrected_text"]

            if context:
                result["transcription_id"] = save_transcription(
                    app_settings.database_path,
                    session_id=context["session_id"],
                    user_id=user["user_id"],
                    question_uid=context["question_uid"],
                    raw_text=correction["raw_text"],
                    corrected_text=correction["corrected_text"],
                    model=str(result.get("model") or "unknown"),
                    runtime=str(result.get("runtime") or "unknown"),
                    confidence=float(result.get("metrics", {}).get("confidence", 0.0)),
                    ambient_noise_dbfs=ambient_noise_dbfs,
                    metadata=result,
                )
            return result
        except TranscriptionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except SpeechToTextError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Lỗi nội bộ: {type(exc).__name__}"},
        )

    return app


app = create_app()
