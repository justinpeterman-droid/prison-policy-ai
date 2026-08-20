from tests.support.web_browser import authenticate_browser, browser_headers


def test_print_template_library_is_authenticated_and_packet_is_read_only(
    api_client,
    db_session,
    db_session_factory,
    fictional_user_account,
    monkeypatch,
):
    anonymous = api_client.get("/api/web/v1/print-templates?period=monthly")
    assert anonymous.status_code == 401

    db_session.commit()
    authenticate_browser(monkeypatch, api_client, db_session_factory, fictional_user_account)
    weekly = api_client.get(
        "/api/web/v1/print-templates?period=weekly",
        headers=browser_headers("print-template-weekly-list"),
    )
    assert weekly.status_code == 200, weekly.get_json()
    assert weekly.get_json()["data"]["items"] == []

    monthly = api_client.get(
        "/api/web/v1/print-templates?period=monthly",
        headers=browser_headers("print-template-monthly-list"),
    )
    assert monthly.status_code == 200, monthly.get_json()
    assert [item["code"] for item in monthly.get_json()["data"]["items"]] == [
        "monthly_windows_bars_doors",
        "monthly_chemical_agents",
        "monthly_contraband_standard",
        "monthly_contraband_expanded",
    ]

    packet = api_client.post(
        "/api/web/v1/print-templates/packet",
        json={
            "period": "monthly",
            "template_codes": [
                "monthly_windows_bars_doors",
                "monthly_chemical_agents",
            ],
            "prefill": {"month": "2026-08", "shift": " D "},
        },
        headers=browser_headers("print-template-packet"),
    )
    assert packet.status_code == 200, packet.get_json()
    assert [item["code"] for item in packet.get_json()["data"]["items"]] == [
        "monthly_windows_bars_doors",
        "monthly_chemical_agents",
    ]
    assert packet.get_json()["data"]["prefill"] == {"month": "2026-08", "shift": "D"}
