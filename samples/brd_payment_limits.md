# Payment Limits Management

## Business goal
- Enable retail customers to view and adjust their payment limits in-app, reducing call-centre volume by 15%.

## Functional
- Customer can view their current daily and per-transaction payment limits.
- Customer can request an increase in their payment limit subject to risk checks.
- Compliance officer can audit all limit changes within the last 12 months.

## Non-functional
- All limit changes must be logged immutably for 7 years.
- The limit-change API must respond within 300ms at p95.
- Authentication must use the existing NatWest SSO; no new credential stores.

## Out of scope
- Business banking customers.
- Cross-currency limit handling.

## Notes
- Edge case behaviour for joint accounts is TBD — needs PO input.
