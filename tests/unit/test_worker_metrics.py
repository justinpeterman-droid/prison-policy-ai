"""Offline contract tests for the RP-07 provider-repeat-risk metric."""

from backend.worker.metrics import GoogleCloudMonitoringMetricSink


class FakeMonitoringClient:
    def __init__(self):
        self.requests = []

    def create_time_series(self, *, request):
        self.requests.append(request)


def test_google_monitoring_sink_writes_exact_repeat_risk_metric_with_bounded_label():
    client = FakeMonitoringClient()
    sink = GoogleCloudMonitoringMetricSink(
        project_id="fictional-project",
        client=client,
        now=lambda: 1_786_665_600,
    )

    sink.increment("ai_provider_repeat_risk_total", labels={"job_type": "generate"})

    assert len(client.requests) == 1
    request = client.requests[0]
    assert request["name"] == "projects/fictional-project"
    series = request["time_series"]
    assert len(series) == 1
    metric = series[0]["metric"]
    assert metric["type"] == "custom.googleapis.com/ai_provider_repeat_risk_total"
    assert metric["labels"] == {"job_type": "generate"}
    assert series[0]["resource"] == {
        "type": "global", "labels": {"project_id": "fictional-project"},
    }
    assert series[0]["points"] == [{
        "interval": {"end_time": {"seconds": 1_786_665_600}},
        "value": {"int64_value": 1},
    }]
