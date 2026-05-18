# Card Freeze & Unfreeze (Mobile)

## Business goal
- Let NatWest retail customers freeze and unfreeze their debit cards instantly from the mobile app, reducing fraud-related call-centre contacts by 25%.

## Functional
- Customer can freeze an active debit card from the card details screen.
- Customer can unfreeze a previously frozen card after passing step-up authentication.
- Compliance officer can audit every freeze and unfreeze event for the last 24 months.

## Non-functional
- Card-state changes must propagate to the authorisation switch within 2 seconds at p95.
- All freeze and unfreeze events must be logged immutably for 7 years.
- Authentication must reuse the existing NatWest SSO; no new credential stores.
- Endpoints must enforce TLS 1.2+ with certificate verification enabled.

## Out of scope
- Credit cards.
- Business banking customers.
- Cross-border card controls.
