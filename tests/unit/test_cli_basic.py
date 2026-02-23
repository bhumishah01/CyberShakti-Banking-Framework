import argparse

from src.app.cli import cmd_add_user, cmd_audit_check, cmd_init_db


def test_cli_basic_flow(tmp_path, capsys) -> None:
    db_path = tmp_path / "cli.db"

    cmd_init_db(argparse.Namespace(db=str(db_path)))
    cmd_add_user(
        argparse.Namespace(
            db=str(db_path),
            user_id="cli-user",
            phone="+919555555555",
            pin="1234",
        )
    )
    cmd_audit_check(argparse.Namespace(db=str(db_path)))

    output = capsys.readouterr().out
    assert "Database initialized" in output
    assert "User created" in output
    assert "Audit chain: VALID" in output
