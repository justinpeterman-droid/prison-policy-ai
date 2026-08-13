from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OPERATIONS = ROOT / "docs" / "operations"

REQUIRED = {
    "external-prerequisites.md": {
        "EXT-01 Separate cloud environments",
        "EXT-08 Managed signing policy",
        "EXT-15 Written production acceptance",
        "EXT-16 GitHub protected environments",
    },
    "workstation-inventory-template.md": {
        "Access version and update channel",
        "Access bitness",
        "Endpoint protection result",
        "Supported or excluded decision",
    },
    "ownership-and-escalation.md": {
        "Business/system owner",
        "Technical service owner",
        "Records-retention authority",
    },
    "environment-register-template.md": {
        "Discovery Engine data store",
        "WIF provider",
        "Secret Manager namespace",
    },
    "github-environment-policy.md": {
        "test | deploy-test.yml, rollback-test.yml, terraform-plan.yml, terraform-apply.yml, bootstrap-first-admin.yml | terraform-plan, terraform-apply, deploy, rollback, admin-bootstrap | 1 | refs/heads/main | CLOSED",
        "production-plan | terraform-plan.yml | terraform-plan | 2 | refs/heads/main | CLOSED",
        "production-apply | terraform-apply.yml | terraform-apply | 2 | refs/heads/main | CLOSED",
        "production-deploy | deploy-production.yml, bootstrap-first-admin.yml | deploy, admin-bootstrap | 2 | refs/heads/main | CLOSED",
        "production-rollback | rollback-production.yml | rollback | 2 | refs/heads/main | CLOSED",
        "access-release | access-release.yml | access-release | 2 | refs/heads/main | CLOSED",
    },
    "release-gates.md": {
        "READY_FOR_TEST",
        "READY_FOR_PRODUCTION",
        "CLOSED",
    },
}


def test_prerequisite_documents_are_complete():
    for filename, required_phrases in REQUIRED.items():
        text = (OPERATIONS / filename).read_text(encoding="utf-8")
        assert all(phrase in text for phrase in required_phrases)
        assert "T" + "BD" not in text
        assert "T" + "ODO" not in text


def test_templates_forbid_real_operational_records_in_git():
    for filename in REQUIRED:
        text = (OPERATIONS / filename).read_text(encoding="utf-8")
        assert "Store completed records in the agency-approved system of record." in text
