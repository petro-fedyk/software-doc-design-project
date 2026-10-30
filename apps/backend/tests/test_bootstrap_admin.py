"""Bootstrap regressions without connecting to or cloning any database."""
from unittest.mock import MagicMock, patch
import pytest
from django.contrib.auth.hashers import check_password
from django.core.management.base import CommandError
from pharmacy.management.commands.bootstrap_admin import Command


def run_command(admin=False, collision=False, lock=True):
    cursor = MagicMock()
    cursor.fetchone.return_value = [1 if lock else 0]
    users = MagicMock()
    users.filter.return_value.exists.side_effect = [admin, collision, False]
    users.create.return_value.id = 123
    with patch('pharmacy.management.commands.bootstrap_admin.connection') as conn, patch('pharmacy.management.commands.bootstrap_admin.Users.objects', users):
        conn.cursor.return_value.__enter__.return_value = cursor
        Command().handle()
    return users, cursor


def test_existing_admin_is_never_reset():
    users, cursor = run_command(admin=True)
    users.create.assert_not_called()
    users.filter.assert_called_once_with(role='ADMIN')
    assert 'RELEASE_LOCK' in cursor.execute.call_args.args[0]


def test_first_admin_has_requested_credentials_hashed():
    users, cursor = run_command()
    data = users.create.call_args.kwargs
    assert data['username'] == 'admin' and data['role'] == 'ADMIN'
    assert data['password'] != 'admin' and check_password('admin', data['password'])
    assert data['is_active'] and data['is_staff']
    assert 'RELEASE_LOCK' in cursor.execute.call_args.args[0]


def test_non_admin_name_collision_fails_without_replacement():
    with pytest.raises(CommandError, match='non-admin'):
        run_command(collision=True)


def test_failed_advisory_lock_does_not_create_user():
    with pytest.raises(CommandError, match='lock'):
        run_command(lock=False)
