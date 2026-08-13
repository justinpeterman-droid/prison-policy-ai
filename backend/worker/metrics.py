"""Safe Cloud Monitoring producer for the RP-07 repeat-risk counter."""

import time


_METRIC_NAME = "ai_provider_repeat_risk_total"
_METRIC_TYPE = f"custom.googleapis.com/{_METRIC_NAME}"


class GoogleCloudMonitoringMetricSink:
    """Write the one bounded application metric required by RP-07.

    The Monitoring client is constructed lazily so local tests can inject a
    fake and no credentials or network access are needed before an event.
    """

    def __init__(self, *, project_id: str, client=None, now=None):
        self._project_id = project_id.strip()
        self._client = client
        self._now = now or time.time

    def _metric_client(self):
        if self._client is None:
            from google.cloud import monitoring_v3

            self._client = monitoring_v3.MetricServiceClient()
        return self._client

    def increment(self, name: str, *, labels: dict[str, str]) -> None:
        """Create exactly one unit-valued custom counter time series."""
        if name != _METRIC_NAME:
            raise ValueError("worker metric name is not approved")
        if set(labels) != {"job_type"} or not isinstance(labels["job_type"], str):
            raise ValueError("worker metric labels are not approved")
        if not self._project_id:
            raise RuntimeError("GCP_PROJECT_ID is required for worker metrics")
        self._metric_client().create_time_series(request={
            "name": f"projects/{self._project_id}",
            "time_series": [{
                "metric": {
                    "type": _METRIC_TYPE,
                    "labels": {"job_type": labels["job_type"]},
                },
                "resource": {
                    "type": "global",
                    "labels": {"project_id": self._project_id},
                },
                "points": [{
                    "interval": {"end_time": {"seconds": int(self._now())}},
                    "value": {"int64_value": 1},
                }],
            }],
        })
