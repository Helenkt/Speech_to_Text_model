import json

from app.database import database
from app.services.account_importer import parse_accounts


def test_account_templates_parse_for_json_csv_and_excel(project_root):
    for suffix in ("json", "csv", "xlsx"):
        path = project_root / "data" / f"account_template.{suffix}"
        accounts, digest = parse_accounts(path.read_bytes(), filename=path.name)
        assert len(accounts) == 2
        assert accounts[0]["role"] == "teacher"
        assert accounts[1]["role"] == "candidate"
        assert len(digest) == 64


def test_vietnamese_headers_and_roles_are_supported():
    document = {
        "users": [
            {
                "ten_dang_nhap": "gv_demo",
                "mat_khau": "secret123",
                "ho_ten": "Giáo viên A",
                "vai_tro": "giao_vien",
                "hoat_dong": "có",
            },
            {
                "ten_dang_nhap": "sv_demo",
                "mat_khau": "secret123",
                "ho_ten": "Ứng viên B",
                "vai_tro": "ứng viên",
                "ma_sinh_vien": "SE123456",
            },
        ]
    }
    accounts, _ = parse_accounts(
        json.dumps(document, ensure_ascii=False).encode(), filename="accounts.json"
    )
    assert [item["role"] for item in accounts] == ["teacher", "candidate"]
    assert accounts[1]["student_id"] == "SE123456"


def test_teacher_imports_accounts_and_database_never_stores_plain_password(
    client, login_teacher, test_settings
):
    csv_content = (
        "username,password,full_name,role,email,student_id,active\n"
        "candidate03,NewPassword,Ứng viên mới,candidate,new@example.com,SV003,true\n"
    ).encode("utf-8")
    response = client.post(
        "/api/teacher/accounts/import",
        data={"mode": "replace"},
        files={"file": ("accounts.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] == 1
    accounts = {item["username"]: item for item in payload["accounts"]}
    assert accounts["teacher"]["active"] is True
    assert accounts["candidate01"]["active"] is False
    assert accounts["candidate03"]["active"] is True
    assert all("password" not in account for account in payload["accounts"])

    with database(test_settings.database_path) as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username = 'candidate03'"
        ).fetchone()
    assert row["password_hash"] != "NewPassword"
    assert row["password_hash"].startswith("scrypt$")

    client.post("/api/auth/logout")
    login = client.post(
        "/api/auth/login",
        json={"username": "candidate03", "password": "NewPassword"},
    )
    assert login.status_code == 200


def test_candidate_cannot_import_account_file(client, login_candidate):
    response = client.post(
        "/api/teacher/accounts/import",
        data={"mode": "upsert"},
        files={"file": ("accounts.csv", b"username,password\na,b\n", "text/csv")},
    )
    assert response.status_code == 403
