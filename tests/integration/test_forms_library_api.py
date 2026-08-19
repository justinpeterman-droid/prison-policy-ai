from tests.support.web_browser import authenticate_browser, browser_headers


def test_forms_library_search_detail_pagination_and_capabilities(
    api_client,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    authenticate_browser(monkeypatch, api_client, db_session_factory, accounts.user)

    first = api_client.get(
        "/api/web/v1/forms?limit=1",
        headers=browser_headers("request_forms_page_1"),
    )
    assert first.status_code == 200
    first_page = first.get_json()["data"]
    assert len(first_page["items"]) == 1
    assert first_page["next_cursor"]
    assert first_page["items"][0]["frequent"] is True

    second = api_client.get(
        f"/api/web/v1/forms?limit=1&cursor={first_page['next_cursor']}",
        headers=browser_headers("request_forms_page_2"),
    )
    assert second.status_code == 200
    assert second.get_json()["data"]["items"][0]["template_id"] != (
        first_page["items"][0]["template_id"]
    )

    search = api_client.get(
        "/api/web/v1/forms?q=medical&category=medical&limit=20",
        headers=browser_headers("request_forms_search"),
    )
    assert search.status_code == 200
    items = search.get_json()["data"]["items"]
    medical = next(
        item for item in items
        if item["code"] == "medical_documentation_checklist"
    )
    assert medical["purpose"]
    assert medical["when_used"]
    assert medical["revision_label"]
    assert {
        "preview",
        "print",
        "download_pdf",
        "fillable",
        "blank",
        "attach_to_incident",
    } <= set(medical["capabilities"])

    detail = api_client.get(
        f"/api/web/v1/forms/{medical['template_id']}",
        headers=browser_headers("request_forms_detail"),
    )
    assert detail.status_code == 200
    assert detail.get_json()["data"]["template_id"] == medical["template_id"]
    assert "definition" in detail.get_json()["data"]


def test_forms_library_selection_preserves_order_and_skips_physical_downloads(
    api_client,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    accounts = fictional_staff_and_accounts
    authenticate_browser(monkeypatch, api_client, db_session_factory, accounts.user)
    catalog = api_client.get(
        "/api/web/v1/forms?limit=50",
        headers=browser_headers("request_forms_selection_catalog"),
    ).get_json()["data"]["items"]
    by_code = {item["code"]: item for item in catalog}
    physical = by_code["chain_of_custody_physical"]
    digital = by_code["medical_documentation_checklist"]

    assert physical["output_kind"] == "physical_only"
    assert physical["capabilities"] == [
        "attach_to_incident",
        "physical_guidance",
    ]
    assert physical["obtain_from"] == "approved paperwork location"

    body = {
        "template_ids": [
            physical["template_id"],
            digital["template_id"],
        ]
    }
    preview = api_client.post(
        "/api/web/v1/forms/selection/preview",
        json=body,
        headers=browser_headers("request_forms_preview"),
    )
    download = api_client.post(
        "/api/web/v1/forms/selection/download",
        json=body,
        headers=browser_headers("request_forms_download"),
    )

    assert preview.status_code == 200
    assert [item["code"] for item in preview.get_json()["data"]["items"]] == [
        "chain_of_custody_physical",
        "medical_documentation_checklist",
    ]
    assert [item["code"] for item in preview.get_json()["data"]["physical_items"]] == [
        "chain_of_custody_physical"
    ]
    assert [item["code"] for item in preview.get_json()["data"]["digital_items"]] == [
        "medical_documentation_checklist"
    ]

    assert download.status_code == 200
    assert [item["code"] for item in download.get_json()["data"]["downloadable_items"]] == [
        "medical_documentation_checklist"
    ]
    assert [item["code"] for item in download.get_json()["data"]["skipped_physical_items"]] == [
        "chain_of_custody_physical"
    ]
    assert "binary" not in download.get_json()["data"]


def test_forms_library_rejects_unknown_duplicate_and_cross_site_selections(
    api_client,
    db_session_factory,
    fictional_staff_and_accounts,
    monkeypatch,
):
    unauthenticated = api_client.get(
        "/api/web/v1/forms?limit=20",
        headers=browser_headers("request_forms_unauthenticated"),
    )
    assert unauthenticated.status_code == 401

    accounts = fictional_staff_and_accounts
    authenticate_browser(monkeypatch, api_client, db_session_factory, accounts.user)
    item = api_client.get(
        "/api/web/v1/forms?limit=1",
        headers=browser_headers("request_forms_one"),
    ).get_json()["data"]["items"][0]

    duplicate = api_client.post(
        "/api/web/v1/forms/selection/preview",
        json={"template_ids": [item["template_id"], item["template_id"]]},
        headers=browser_headers("request_forms_duplicate"),
    )
    assert duplicate.status_code == 400

    cross_site_headers = browser_headers("request_forms_cross_site")
    cross_site_headers["Origin"] = "https://attacker.example"
    cross_site_headers["Sec-Fetch-Site"] = "cross-site"
    cross_site = api_client.post(
        "/api/web/v1/forms/selection/preview",
        json={"template_ids": [item["template_id"]]},
        headers=cross_site_headers,
    )
    assert cross_site.status_code == 403
