# FUW pilot dataset

The controlled-pilot workbook is intentionally **not stored in this public repository**.
It contains temporary account credentials and research-operations data.

The private copy is generated into `/home/user/fuw-pilot-sandbox/` and includes a SHA-256
checksum, a wipe manifest, sources, academic structure, account rosters, controlled cases,
blank processing logs and survey instruments. The live database stores an internal
`data_origin` and cohort marker so controlled cases can be excluded from operational
research exports and removed before launch.

Never commit the workbook, passwords, participant rosters, database exports or rollback
snapshots. A sanitised schema or empty template may be committed only after every value
has been checked for credentials and personal data.
