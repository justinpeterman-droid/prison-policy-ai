from backend.jobs import migration


def test_production_migration_runner_has_no_downgrade_subcommand():
    assert migration.main(["downgrade"]) != 0
