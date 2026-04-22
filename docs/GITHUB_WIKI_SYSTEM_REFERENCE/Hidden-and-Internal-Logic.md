# Hidden and Internal Logic

## Important Internal Helpers

Key helpers in `src/ui/app.py` do significant system work even though they are not visible as main features:

- customer dashboard assembly
- admin dashboard assembly
- fraud trends aggregation
- risk distribution calculation
- top fraud reason aggregation
- user-wise analytics calculation
- transaction row formatting
- flash message reading/clearing
- voice command parsing
- friendly label formatting

## Audit + Change Tracking

The system maintains both:
- a tamper-evident audit chain
- a readable field-level change log

These serve different purposes and operate in parallel.

## Monitoring Side Effects

Subsystems such as auth and transactions create alerts and notifications behind the scenes. These are not single-feature behaviors; they are cross-cutting observability behavior.

## Schema Upgrade Behavior

`init_db()` is not only initialization logic. It also acts as a lightweight schema backfill system by adding missing columns to older databases.

## Trusted Device Face Refresh Logic

On trusted devices, face-template refresh is allowed in some login situations to avoid demo-breaking false mismatches from camera or lighting drift.

## Legacy Support

The codebase keeps earlier/legacy routes and backend paths active so older links and earlier integration stages still function.
