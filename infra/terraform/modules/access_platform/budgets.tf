resource "google_billing_budget" "access" {
  billing_account = var.billing_account_id
  display_name    = "Access ${var.environment} ${var.observability_owner_role} budget"
  # The budget remains isolated to this environment's approved project and
  # displays the owner role without embedding a person or contact target.
  budget_filter {
    projects = ["projects/${var.project_id}"]
    labels = {
      environment = var.environment
      owner_role  = var.observability_owner_role
    }
  }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_amount)
    }
  }

  dynamic "threshold_rules" {
    for_each = [0.5, 0.8, 0.9, 1.0, 1.2]

    content {
      threshold_percent = threshold_rules.value
    }
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  all_updates_rule {
    pubsub_topic                   = var.budget_pubsub_topic
    schema_version                 = "1.0"
    disable_default_iam_recipients = true
  }

  depends_on = [google_project_service.required]
}
