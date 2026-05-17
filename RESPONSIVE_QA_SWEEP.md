# Responsive QA Sweep

Date: 2026-05-17
Method: Static CSS/HTML audit (breakpoints, fluid layout rules, overflow handling, stacking behavior, viewport tags).

## Compact Checklist

1. Viewport meta present.
2. Desktop layout remains multi-column or full-content at >=1024px.
3. Tablet breakpoint exists around <=980px and reorganizes major grids/panels.
4. Phone breakpoint exists around <=700px and stacks nav/actions/forms.
5. Wide content has horizontal overflow handling where needed (tables, tabs, data grids).
6. Touch controls become usable on small screens (full-width or stacked where appropriate).

## Pass/Fail Matrix

| Template | Phone | Tablet | Desktop | Notes |
|---|---|---|---|---|
| Farmers/templates/Farmers/admin_dashboard.html | PASS | PASS | PASS | 980/680/520 tiers, table min-width with scroll wrapper, stacked actions at small width. |
| Farmers/templates/Farmers/farmer_dashboard.html | PASS | PASS | PASS | 900/640 tiers, sidebar collapse, mobile table scroll, single-column forms/stats. |
| Farmers/templates/Farmers/partner_dashboard.html | PASS | PASS | PASS | 980/680 tiers, tab overflow, drawer scaling, data tables wrapped with overflow-x. |
| Farmers/templates/Farmers/inbox.html | PASS | PASS | PASS | 980/700/520 tiers, sidebar-to-stack behavior, compose and modal actions stack on phone. |
| Farmers/templates/Farmers/create_user.html | PASS | PASS | PASS | 820/620 tiers, navbar wraps, full-width submit on phone. |
| Farmers/templates/Farmers/broadcast.html | PASS | PASS | PASS | 920/640 tiers, audience cards collapse 3->2->1, action buttons stack on phone. |
| Farmers/templates/Farmers/contact_submissions_admin.html | PASS | PASS | PASS | 980/760/520 tiers, table scroll strategy, compact pagination/top actions on phone. |
| Farmers/templates/Farmers/assign_farmer_request.html | PASS | PASS | PASS | 820/620 tiers, navbar wraps, full-width primary action on phone. |
| Farmers/templates/Farmers/create_farmer.html | PASS | PASS | PASS | 980/760/520 tiers, image-choice grid collapse, stacked action bar on phone. |
| Farmers/templates/Farmers/password_reset.html | PASS | PASS | PASS | Fluid card width and <=560 optimization with full-width button. |
| Farmers/templates/Farmers/password_reset_confirm.html | PASS | PASS | PASS | Fluid card width and <=560 optimization with full-width button. |
| Farmers/templates/Farmers/password_reset_done.html | PASS | PASS | PASS | Fluid centered card, viewport present, <=560 typography/padding optimization. |
| Farmers/templates/Farmers/password_reset_complete.html | PASS | PASS | PASS | Fluid centered card, viewport present, <=560 typography/padding optimization. |
| Farmers/templates/Farmers/force_password_change.html | PASS | PASS | PASS | Base fluid card plus <=640 small-screen button stacking. |
| Farmers/templates/Farmers/request_password_reset_from_admin.html | PASS | PASS | PASS | Base fluid card plus <=640 small-screen button stacking. |
| Farmers/templates/Farmers/superuser_dashboard_gate.html | PASS | PASS | PASS | <=680 action stack and full-width controls for phone. |
| Farmers/templates/Farmers/superuser_dashboard_selector.html | PASS | PASS | PASS | 980/680/520 grid collapse and full-width actions at small widths. |

## Residual Risks

1. Partner tables intentionally keep large min-width values and rely on horizontal scroll on phone.
2. Final visual polish still benefits from manual browser/device checks for exact spacing preferences.

## Recommended Quick Manual Spot Check

1. 390x844 phone viewport: admin dashboard, inbox, partner admin/data governance table.
2. 768x1024 tablet viewport: partner dashboard tabs and create farmer form sections.
3. 1366x768 desktop viewport: overall density/readability across dashboard cards and tables.

## Visual Verification Sweep (Screenshot-Style)

Sweep run: 2026-05-17
Viewports: 390x844 (phone), 768x1024 (tablet), 1366x768 (desktop)
Approach: Playwright-driven capture plus layout metrics (horizontal overflow, clipped element heuristic).

### Overall Result

1. Horizontal overflow: PASS across captured routes (no page-level horizontal overflow detected).
2. Responsive breakpoint transitions: PASS across captured routes.
3. Caution flags:
	- Admin dashboard reported clipped interactive count at all widths (likely due hidden/off-canvas sidebar controls).
	- Partner dashboard reported clipped interactive count at all widths (likely due side drawers and off-canvas controls).
4. Access limitation:
	- force_password_change route could not be directly rendered with superuser QA account during this sweep (redirected to selector).

### Findings Matrix (with screenshots)

| Template Route | 390 | 768 | 1366 | Finding |
|---|---|---|---|---|
| superuser_dashboard_selector | [390](.qa-screenshots/superuser_selector_390.png) | [768](.qa-screenshots/superuser_selector_768.png) | [1366](.qa-screenshots/superuser_selector_1366.png) | PASS |
| superuser_dashboard_gate (template view) | [390](.qa-screenshots/superuser_gate_template_390.png) | [768](.qa-screenshots/superuser_gate_template_768.png) | [1366](.qa-screenshots/superuser_gate_template_1366.png) | PASS |
| admin_dashboard | [390](.qa-screenshots/admin_dashboard_390.png) | [768](.qa-screenshots/admin_dashboard_768.png) | [1366](.qa-screenshots/admin_dashboard_1366.png) | PASS with caution (clipped heuristic) |
| assign_farmer_request | [390](.qa-screenshots/assign_farmer_request_390.png) | [768](.qa-screenshots/assign_farmer_request_768.png) | [1366](.qa-screenshots/assign_farmer_request_1366.png) | PASS |
| create_user | [390](.qa-screenshots/create_user_390.png) | [768](.qa-screenshots/create_user_768.png) | [1366](.qa-screenshots/create_user_1366.png) | PASS |
| contact_submissions_admin | [390](.qa-screenshots/contact_submissions_admin_390.png) | [768](.qa-screenshots/contact_submissions_admin_768.png) | [1366](.qa-screenshots/contact_submissions_admin_1366.png) | PASS |
| inbox | [390](.qa-screenshots/inbox_390.png) | [768](.qa-screenshots/inbox_768.png) | [1366](.qa-screenshots/inbox_1366.png) | PASS |
| broadcast | [390](.qa-screenshots/broadcast_390.png) | [768](.qa-screenshots/broadcast_768.png) | [1366](.qa-screenshots/broadcast_1366.png) | PASS |
| create_farmer | [390](.qa-screenshots/create_farmer_390.png) | [768](.qa-screenshots/create_farmer_768.png) | [1366](.qa-screenshots/create_farmer_1366.png) | PASS |
| farmer_dashboard | [390](.qa-screenshots/farmer_dashboard_390.png) | [768](.qa-screenshots/farmer_dashboard_768.png) | [1366](.qa-screenshots/farmer_dashboard_1366.png) | PASS |
| partner_dashboard | [390](.qa-screenshots/partner_dashboard_390.png) | [768](.qa-screenshots/partner_dashboard_768.png) | [1366](.qa-screenshots/partner_dashboard_1366.png) | PASS with caution (clipped heuristic) |
| password_reset | [390](.qa-screenshots/password_reset_390.png) | [768](.qa-screenshots/password_reset_768.png) | [1366](.qa-screenshots/password_reset_1366.png) | PASS |
| password_reset_done | [390](.qa-screenshots/password_reset_done_390.png) | [768](.qa-screenshots/password_reset_done_768.png) | [1366](.qa-screenshots/password_reset_done_1366.png) | PASS |
| password_reset_complete | [390](.qa-screenshots/password_reset_complete_390.png) | [768](.qa-screenshots/password_reset_complete_768.png) | [1366](.qa-screenshots/password_reset_complete_1366.png) | PASS |
| password_reset_confirm (invalid-token state) | [390](.qa-screenshots/password_reset_confirm_390.png) | [768](.qa-screenshots/password_reset_confirm_768.png) | [1366](.qa-screenshots/password_reset_confirm_1366.png) | PASS |
| request_password_reset_from_admin | [390](.qa-screenshots/request_password_reset_from_admin_390.png) | [768](.qa-screenshots/request_password_reset_from_admin_768.png) | [1366](.qa-screenshots/request_password_reset_from_admin_1366.png) | PASS |
| force_password_change | [390](.qa-screenshots/force_password_change_390.png) | [768](.qa-screenshots/force_password_change_768.png) | [1366](.qa-screenshots/force_password_change_1366.png) | BLOCKED (redirected to selector in QA session) |

### Notes

1. Vertical overflow on long pages (forms/dashboards) is expected and not treated as a failure.
2. This pass used an authenticated QA superuser account to reach protected views.
