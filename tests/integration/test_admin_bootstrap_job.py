from backend.jobs.admin_bootstrap import AdminBootstrapResult


def test_bootstrap_result_is_a_closed_safe_contract():
    assert set(AdminBootstrapResult.__annotations__) == {"operation_id", "status", "expires_at", "secret_version_reference"}
