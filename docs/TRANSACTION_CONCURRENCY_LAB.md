# InfraAssess Phase 4: Transactions and concurrency lab

This lab uses PostgreSQL 18.6 and two separate `psql` sessions. It does not lock or delete project rows. The demonstration table is disposable and must be created and dropped explicitly.

## Transaction tests

Run the automated transaction checks after the Phase 3 objects exist:

```bash
psql -X --set ON_ERROR_STOP=1 -d infraassess_test \
  -f database/transaction_tests.sql
```

The script verifies committed temporary data, rolled-back temporary data, atomic failure of `sp_complete_work_order`, and a successful completion workflow that is rolled back before the seeded work order is rechecked.

## Lock setup

In one terminal, create the disposable table and a row:

```bash
psql -X -d infraassess_test
```

```sql
CREATE TABLE IF NOT EXISTS transaction_concurrency_lab (
    id integer PRIMARY KEY,
    value integer NOT NULL
);
INSERT INTO transaction_concurrency_lab(id, value) VALUES (1, 100)
ON CONFLICT (id) DO UPDATE SET value = EXCLUDED.value;
```

Open a second terminal with another connection:

```bash
psql -X -d infraassess_test
```

## `FOR UPDATE`, `NOWAIT`, and recovery

Session A acquires a row lock and keeps the transaction open:

```sql
BEGIN;
SELECT * FROM transaction_concurrency_lab WHERE id=1 FOR UPDATE;
UPDATE transaction_concurrency_lab SET value=value+10 WHERE id=1;
```

Session B attempts the same lock without waiting:

```sql
BEGIN;
SELECT * FROM transaction_concurrency_lab WHERE id=1 FOR UPDATE NOWAIT;
```

Expected result: an error such as `could not obtain lock on row in relation "transaction_concurrency_lab"`, SQLSTATE `55P03`. The transaction is aborted after that error, so recover it with:

```sql
ROLLBACK;
```

Session A can now finish its work:

```sql
COMMIT;
```

If `NOWAIT` is not used, set a bounded timeout before attempting the lock:

```sql
BEGIN;
SET LOCAL lock_timeout = '2s';
SELECT * FROM transaction_concurrency_lab WHERE id=1 FOR UPDATE;
ROLLBACK;
```

The timeout prevents a hung demonstration. Session B can also inspect available work without waiting:

```sql
BEGIN;
SELECT * FROM transaction_concurrency_lab WHERE id=1 FOR UPDATE SKIP LOCKED;
ROLLBACK;
```

With the row locked by Session A, this returns zero rows rather than an error. `SKIP LOCKED` is useful for work queues where another worker can process a different available row. It is not appropriate when every requested row must be processed.

Locks acquired by a transaction are released at `COMMIT` or `ROLLBACK`; they are not released merely because a statement finishes.

## Isolation visibility experiment

Reset the row in either session:

```sql
UPDATE transaction_concurrency_lab SET value=100 WHERE id=1;
```

Use Session A with the default `READ COMMITTED` isolation:

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT value FROM transaction_concurrency_lab WHERE id=1; -- 100
```

In Session B:

```sql
BEGIN;
UPDATE transaction_concurrency_lab SET value=200 WHERE id=1;
COMMIT;
```

Back in Session A, run the same `SELECT`. It sees `200` because each statement in `READ COMMITTED` gets a new snapshot. Finish with `COMMIT` or `ROLLBACK`.

Repeat with Session A using `REPEATABLE READ`:

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT value FROM transaction_concurrency_lab WHERE id=1; -- establish snapshot
```

Have Session B update the row to `300` and commit. Repeating the `SELECT` in Session A still sees the earlier value because the transaction keeps one snapshot. At `REPEATABLE READ`, a concurrent update to the same row can also cause a serialization failure (`40001`) rather than silently allowing a lost update. Recover an aborted transaction with `ROLLBACK`, then retry the complete transaction if appropriate.

## Cleanup

After all experiments, run this in either session:

```sql
DROP TABLE transaction_concurrency_lab;
```

Do not use `DROP ... CASCADE`, and do not substitute a production InfraAssess table.
