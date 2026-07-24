"""Analytics module — demand forecasting v1 + reorder suggestions (Sprint 7).

Internal management tool, zero legal risk (PROJECT_STATE §7am). Forecasts demand as a
90-day moving average per drug×branch, computes a reorder point, and suggests draft
purchase orders when projected stock falls below it — never auto-sends to a supplier
(the philosophy is "cảnh báo không chặn": suggest, a human approves).

Reads sales/inventory/procurement only through its own ports (module-independence);
the adapters live at the composition root (``api/v1/analytics_wiring.py``), so
analytics never imports another business module.
"""
