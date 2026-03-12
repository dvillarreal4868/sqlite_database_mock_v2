# Clinical Data Registry — Implementation Guide

## Overview

This project builds a SQLite-based metadata registry for tracking patient health information across multiple IRB studies. Patient data arrives in batches tied to IRB protocols, containing a mix of Electronic Health Records (EHRs) and imaging data (CTs, MRIs). Not all data arrives at once — text records typically arrive first, imaging later — and the registry tracks what we have, what we're waiting on, and when things changed.

The registry does **not** store patient data itself. It stores pointers (file paths) to where the data lives and metadata about its completeness. Think of it as a ledger, not a warehouse.

We use DVC (Data Version Control) to version the registry database, allowing us to snapshot its state over time and roll back if needed.

---

## Progress Tracker

<details>
<summary><strong>Phase 1: Initial Setup</strong></summary>

- [X] 1.1 — Initialize the project repository
- [x] 1.2 — Initialize DVC
- [x] 1.3 — Create the database and define the schema
- [x] 1.4 — Version the empty database with DVC

</details>

<details>
<summary><strong>Phase 2: First Data Arrival (IRB 1 & IRB 2)</strong></summary>

- [x] 2.1 — Generate mock data for IRB 1 and IRB 2
- [x] 2.2 — Parse the raw data into a dataframe
- [ ] 2.3 — Populate the patient_registry table
- [ ] 2.4 — Populate the data_assets table
- [ ] 2.5 — Run your first completeness report
- [ ] 2.6 — Version the populated database with DVC

</details>

<details>
<summary><strong>Phase 3: Later Data Arrival (IRB 3)</strong></summary>

- [ ] 3.1 — Generate mock data for IRB 3
- [ ] 3.2 — Parse IRB 3 and identify what's new
- [ ] 3.3 — Ingest IRB 3 into the registry
- [ ] 3.4 — Reconciliation report
- [ ] 3.5 — Decide on and implement backfill strategy
- [ ] 3.6 — Version the updated database with DVC

</details>

<details>
<summary><strong>Phase 4: Hardening the System</strong></summary>

- [ ] 4.1 — Write the ingestion script
- [ ] 4.2 — Write basic tests
- [ ] 4.3 — Write the data dictionary
- [ ] 4.4 — Write the runbook

</details>

<details>
<summary><strong>Phase 5: Ongoing Operations</strong></summary>

- [ ] Confirm the full workflow runs end-to-end
- [ ] Onboard at least one other team member using the README

</details>

---

<details>
<summary><h2>Project Structure</h2></summary>

```
project/
├── data/
│   ├── raw/
│   │   ├── irb_2025_001/
│   │   │   ├── ehr/
│   │   │   ├── ct/
│   │   │   └── mri/
│   │   ├── irb_2025_002/
│   │   │   ├── ehr/
│   │   │   ├── ct/
│   │   │   └── mri/
│   │   └── irb_2025_003/
│   │       ├── ehr/
│   │       ├── ct/
│   │       └── mri/
│   └── processed/
├── db/
│   ├── registry.db
│   ├── setup_registry.py
│   ├── connections.yaml
│   └── README_data_dictionary.md
├── src/
│   ├── generate_mock_data.py
│   ├── ehr_parser/
│   ├── ingest_batch.py
│   └── completeness_report.py
├── tests/
│   └── test_ingestion.py
├── requirements.txt
├── .gitignore
├── .dvc/
└── registry.db.dvc
```

</details>

<details>
<summary><h2>Prerequisites</h2></summary>

- Python 3.9+
- pip packages: `pandas`, `pyyaml`, `dvc` (see `requirements.txt`)
- A basic understanding of SQL (SELECT, INSERT, UPDATE)
- DVC installed and initialized in the repo

</details>

---

<details>
<summary><h2>Phase 1: Initial Setup</h2></summary>

<details>
<summary><strong>Step 1.1 — Initialize the project repository</strong></summary>

- Create the directory structure shown above.
- Run `git init` if not already a git repo.
- Create a `.gitignore` that excludes `registry.db`, `*.db`, and `data/raw/` (raw patient data should not live in git).
- Run `pip install -r requirements.txt` to install dependencies.

</details>

<details>
<summary><strong>Step 1.2 — Initialize DVC</strong></summary>

- Run `dvc init` inside the project root. This creates the `.dvc/` directory.
- Configure your DVC remote — this is where versioned snapshots of the registry will be stored. This could be a local directory, a network drive, or cloud storage (S3, GCS, Azure Blob).
- Run `dvc remote add -d myremote /path/to/your/dvc-storage` for a local remote, or substitute with your cloud URI.
- Commit the DVC config to git: `git add .dvc/ .dvcignore && git commit -m "Initialize DVC"`.

</details>

<details>
<summary><strong>Step 1.3 — Create the database and define the schema</strong></summary>

- Write `db/setup_registry.py`. This script:
  - Connects to `db/registry.db` (creates the file if it doesn't exist).
  - Creates the `patient_registry` table with columns: `patient_id`, `irb_id`, `irb_server`, `enrolled_date`. Primary key is `(patient_id, irb_id)`.
  - Creates the `data_assets` table with columns: `id` (autoincrement), `patient_id`, `irb_id`, `modality`, `asset_uri`, `status`, `received_date`. Unique constraint on `(patient_id, irb_id, modality)`. Foreign key referencing `patient_registry`. CHECK constraints on `modality` and `status`.
  - Creates the `change_log` table with columns: `id` (autoincrement), `timestamp`, `table_name`, `record_key`, `field_changed`, `old_value`, `new_value`, `action`.
  - Creates automatic triggers on `data_assets` so that any INSERT or UPDATE writes to `change_log` without manual intervention.
  - Commits and closes the connection.
- Run the script once: `python db/setup_registry.py`.
- Verify by opening `registry.db` in DB Browser for SQLite and confirming the three tables exist with the correct columns.

</details>

<details>
<summary><strong>Step 1.4 — Version the empty database with DVC</strong></summary>

- Run `dvc add db/registry.db`. This creates `db/registry.db.dvc`, a small pointer file.
- Run `git add db/registry.db.dvc db/.gitignore && git commit -m "Empty registry schema"`.
- Run `dvc push` to push the database snapshot to your remote.
- This is your baseline. You can always return to this empty state with `dvc checkout`.

</details>

</details>

---

<details>
<summary><h2>Phase 2: Simulating the First Data Arrival (IRB 1 & IRB 2)</h2></summary>

<details>
<summary><strong>Step 2.1 — Generate mock data for IRB 1 and IRB 2</strong></summary>

- Write or update `scripts/generate_mock_data.py` to only generate data for IRB-2025-001 and IRB-2025-002.
- Run the script. Confirm the files land in `data/raw/irb_2025_001/` and `data/raw/irb_2025_002/` with the expected subdirectories (ehr/, ct/, mri/).
- Spot-check a few files to make sure content looks reasonable.

</details>

<details>
<summary><strong>Step 2.2 — Parse the raw data into a dataframe</strong></summary>

- Use `scripts/ehr_parser.py` (or extend it into a general parser) to scan the IRB directories.
- For each IRB directory, scan all three modality subdirectories (ehr/, ct/, mri/).
- Extract the patient ID from each filename (split on underscore, take the first part).
- For each patient in each IRB, create a row for every expected modality:
  - If a file exists for that modality: set `asset_uri` to the file path and `status` to `"complete"`.
  - If no file exists: set `asset_uri` to `None` and `status` to `"pending"`.
- Output a single dataframe in long format with columns: `patient_id`, `irb_id`, `modality`, `asset_uri`, `status`, `received_date`.
- Verify the shape makes sense. IRB 1 has 10 patients × 3 modalities = 30 rows. IRB 2 has 10 patients × 3 modalities = 30 rows. Total: 60 rows.

</details>

<details>
<summary><strong>Step 2.3 — Populate the patient_registry table</strong></summary>

- Extract unique `(patient_id, irb_id)` pairs from the dataframe.
- Derive `irb_server` from the IRB directory path (e.g., `"srv://irb-2025-001"`).
- Set `enrolled_date` to today's date or extract from the file metadata.
- Insert into `patient_registry` using `df.to_sql()` or individual INSERT statements with `INSERT OR IGNORE` to skip duplicates.
- Verify: query the table and confirm 20 rows (10 from IRB 1, 10 from IRB 2, with 4 patients appearing in both).

</details>

<details>
<summary><strong>Step 2.4 — Populate the data_assets table</strong></summary>

- Take the full long-format dataframe from Step 2.2.
- Insert into `data_assets` using `df.to_sql()` with `if_exists="append"`.
- Verify by querying:
  - Total row count should be 60.
  - IRB 1 should have 10 complete EHRs, 6 complete CTs, 10 pending MRIs, and 4 pending CTs.
  - IRB 2 should have 10 complete EHRs, 7 complete MRIs, 10 pending CTs, and 3 pending MRIs.

</details>

<details>
<summary><strong>Step 2.5 — Run your first completeness report</strong></summary>

- Query the database to produce a summary per patient showing status by modality.
- Confirm the gaps match what you expect:
  - PAT-002: has EHR from both IRBs, CT pending from IRB 1, MRI complete from IRB 2.
  - PAT-007: has EHR from both IRBs, CT and MRI pending from IRB 1, CT and MRI pending from IRB 2.
  - Patients unique to IRB 1 (PAT-001, 003, 004, 006, 008, 009): no MRI data at all.
- This is your "before" snapshot.

</details>

<details>
<summary><strong>Step 2.6 — Version the populated database with DVC</strong></summary>

- Run `dvc add db/registry.db`.
- Run `git add db/registry.db.dvc && git commit -m "Registry after IRB 1 and IRB 2 ingestion"`.
- Run `dvc push`.
- You now have two snapshots: the empty schema and the state after the first two IRBs.

</details>

</details>

---

<details>
<summary><h2>Phase 3: Simulating a Later Data Arrival (IRB 3)</h2></summary>

<details>
<summary><strong>Step 3.1 — Generate mock data for IRB 3</strong></summary>

- Update `scripts/generate_mock_data.py` to generate IRB-2025-003 data (or run it with a flag/argument that generates only IRB 3).
- Run the script. Confirm files land in `data/raw/irb_2025_003/` with all three modality folders populated.
- Note that IRB 3 has complete data (EHR + CT + MRI) for all its patients, and several of those patients overlap with IRB 1 and IRB 2.

</details>

<details>
<summary><strong>Step 3.2 — Parse IRB 3 and identify what's new</strong></summary>

- Run the parser against `data/raw/irb_2025_003/` only.
- Produce the long-format dataframe for IRB 3: 10 patients × 3 modalities = 30 rows, all with status "complete."
- Before inserting, query the database to understand the current state. Identify:
  - **New patients** not yet in the registry (PAT-017, 018, 019, 020). These need full inserts into both tables.
  - **Existing patients with new IRB enrollment** (PAT-002, 005, 007, 010, 011, 016 under IRB 3). These need new rows in `patient_registry` and new rows in `data_assets` for the IRB 3 records.
- This comparison step is important. It's the difference between blindly appending and intelligently merging.

</details>

<details>
<summary><strong>Step 3.3 — Ingest IRB 3 into the registry</strong></summary>

- Insert new patient-IRB pairs into `patient_registry` (using INSERT OR IGNORE to handle any edge cases).
- Insert the 30 new `data_assets` rows for IRB 3.
- The triggers you set up in Step 1.3 will automatically log all of these inserts to the `change_log`.
- Verify:
  - `patient_registry` should now have 30 rows (10 + 10 + 10, with overlaps handled by unique IRB-patient pairs).
  - `data_assets` should now have 90 rows (60 from before + 30 new).

</details>

<details>
<summary><strong>Step 3.4 — Reconciliation report</strong></summary>

- Run the completeness report again.
- Compare against the Phase 2 report. You should see:
  - PAT-017 through PAT-020 are now in the system, fully complete under IRB 3.
  - PAT-007 still shows pending CT and MRI under IRB 1 — those older records haven't changed. But under IRB 3, the same patient now has complete data.
  - The system correctly shows the same patient can have different completeness states under different IRBs.
- This is your "after" snapshot.

</details>

<details>
<summary><strong>Step 3.5 — Optional: backfill pending records from earlier IRBs</strong></summary>

- This is a judgment call. PAT-007 has a pending CT under IRB 1, but IRB 3 delivered a CT for PAT-007. Do you want to update the IRB 1 record to point to the IRB 3 file? Or leave it as pending because the data technically belongs to a different protocol?
- If you decide to backfill:
  - Query for patients with pending modalities in earlier IRBs who now have complete records in later IRBs.
  - Update those rows: set `asset_uri` to the new file path and `status` to `"complete"`.
  - The trigger captures this automatically in `change_log`.
- If you decide not to backfill: the registry is still correct — it just tracks completeness per IRB rather than per patient globally. Either approach is valid. Document your decision in the README so the next person understands the convention.

</details>

<details>
<summary><strong>Step 3.6 — Version the updated database with DVC</strong></summary>

- Run `dvc add db/registry.db`.
- Run `git add db/registry.db.dvc && git commit -m "Registry after IRB 3 ingestion"`.
- Run `dvc push`.
- You now have three snapshots. You can diff between any two to see exactly what changed between ingestion events.

</details>

</details>

---

<details>
<summary><h2>Phase 4: Hardening the System</h2></summary>

<details>
<summary><strong>Step 4.1 — Write the ingestion script</strong></summary>

- Consolidate your parsing and insertion logic into `scripts/ingest_batch.py`.
- It should accept an argument for the IRB directory path.
- The script should:
  - Parse the directory and produce the long-format dataframe.
  - Connect to `registry.db`.
  - Insert new patient-IRB pairs into `patient_registry`.
  - Insert new data asset rows into `data_assets`.
  - Print a summary: how many new patients, how many new assets, how many records updated.
  - Commit and close.
- This becomes the single entry point for all future ingestion. When IRB 4 arrives, anyone on the team runs: `python scripts/ingest_batch.py --irb-dir data/raw/irb_2025_004`.

</details>

<details>
<summary><strong>Step 4.2 — Write basic tests</strong></summary>

- Create `tests/test_ingestion.py`.
- The test script should:
  - Create a fresh temporary `registry.db` using `setup_registry.py`.
  - Run the ingestion against the mock IRB 1 and IRB 2 data.
  - Assert expected row counts in each table.
  - Assert that known overlap patients (PAT-002, 005, 007, 010) appear in both IRBs.
  - Assert that pending/complete counts match expectations.
  - Run the ingestion for IRB 3.
  - Assert updated row counts and completeness.
  - Assert that the change_log has entries.
- Run with `python -m pytest tests/` or simply `python tests/test_ingestion.py`.
- These tests give the next person confidence to modify the ingestion without fear.

</details>

<details>
<summary><strong>Step 4.3 — Write the data dictionary</strong></summary>

- Create `db/README_data_dictionary.md` documenting every table and column:
  - `patient_registry`: what each column means, what the primary key enforces, example values.
  - `data_assets`: what each column means, allowed values for `modality` and `status`, what the foreign key enforces, what the unique constraint prevents.
  - `change_log`: what gets logged, when, and how to read it.
- Include example queries for common tasks: finding pending records, checking a specific patient, running a completeness summary.

</details>

<details>
<summary><strong>Step 4.4 — Write the runbook</strong></summary>

- Add a section to this README or create a separate `RUNBOOK.md` with step-by-step instructions for:
  - **New IRB batch arrives**: run the ingestion script, verify with completeness report, version with DVC.
  - **Checking data completeness**: run the completeness report script.
  - **Recovering from a bad ingestion**: use `dvc checkout` to roll back to the previous version of `registry.db`, fix the issue, re-ingest.
  - **Adding a new modality**: update the CHECK constraint in the schema, update the parser, re-run setup (the IF NOT EXISTS clauses make this safe).
  - **Rebuilding the database from scratch**: delete `registry.db`, run `setup_registry.py`, re-ingest all IRBs in order.

</details>

</details>

---

<details>
<summary><h2>Phase 5: Ongoing Operations</h2></summary>

<details>
<summary><strong>When new data arrives</strong></summary>

1. Place the new IRB directory in `data/raw/`.
2. Run `python scripts/ingest_batch.py --irb-dir data/raw/irb_2025_XXX`.
3. Run `python scripts/completeness_report.py` to verify.
4. Version: `dvc add db/registry.db && git add db/registry.db.dvc && git commit -m "Ingested IRB-2025-XXX" && dvc push`.

</details>

<details>
<summary><strong>When checking status</strong></summary>

1. Run `python scripts/completeness_report.py` or connect to `registry.db` directly with DB Browser or pandas.

</details>

<details>
<summary><strong>When something goes wrong</strong></summary>

1. Check the `change_log` table to understand what happened and when.
2. If the database is corrupted: `dvc checkout db/registry.db` to restore the last good version.
3. If you need to rebuild entirely: delete `registry.db`, run `setup_registry.py`, re-ingest all IRBs chronologically.

</details>

<details>
<summary><strong>When adding a new team member</strong></summary>

1. They clone the git repo.
2. They run `pip install -r requirements.txt`.
3. They run `dvc pull` to get the latest `registry.db`.
4. They read this README and the data dictionary.
5. They're operational.

</details>

</details>

---

<details>
<summary><h2>DVC Cheat Sheet</h2></summary>

| Action | Command |
|---|---|
| Track the registry | `dvc add db/registry.db` |
| Push to remote | `dvc push` |
| Pull latest version | `dvc pull` |
| View version history | `git log db/registry.db.dvc` |
| Restore a previous version | `git checkout <commit> db/registry.db.dvc && dvc checkout` |
| See what changed | `dvc diff` |

</details>

---

<details>
<summary><h2>Key Design Decisions</h2></summary>

- **The registry tracks metadata, not data.** It stores file paths, not file contents. This keeps the database small and avoids duplicating PHI inside the registry itself.
- **One row per patient per IRB per modality in data_assets.** This long format allows new modalities to be added without changing the schema.
- **Pending rows are created at enrollment.** When a patient is enrolled, rows for all expected modalities are created immediately — even before the data exists. This lets us query for what's missing, not just what's present.
- **The change log is append-only and trigger-driven.** No one needs to remember to log changes. The database handles it automatically.
- **DVC versions the database, not git.** The database is a binary file that changes frequently. Git would bloat; DVC handles this efficiently with deduplication and remote storage.

</details>
