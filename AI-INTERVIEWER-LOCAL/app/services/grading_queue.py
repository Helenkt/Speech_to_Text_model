"""Enqueue confirmed answers without changing existing grading decisions or attempts."""


def queue_session_grading(connection, session_id=None):
    """A null session selects eligible completed sessions in the caller's transaction."""
    connection.execute("""INSERT OR IGNORE INTO session_grading_jobs (session_id)
        SELECT s.session_id FROM interview_sessions s
        WHERE (? IS NULL OR s.session_id=?) AND s.status='completed'
          AND s.grading_strategy='end_of_session'
          AND EXISTS (SELECT 1 FROM interview_answers a
              WHERE a.session_id=s.session_id AND a.grading_pending=1)""",
        (session_id, session_id))
