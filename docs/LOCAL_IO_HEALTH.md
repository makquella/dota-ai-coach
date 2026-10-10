# Local persistence failure handling (0.53.44)

Census captures one summary under its short memory owner, then writes outside
that owner. A unique same-directory temporary JSON file is replaced only after
complete serialization/write. The observed packet count and save time are
acknowledged only after successful replacement. One attempt may be pending;
failed attempts wait five seconds before the next `save_due` call can retry,
including without a new packet. Regular saves retain the 30-second interval.
Live summary exposes pending, acknowledged count, failures and error type.

The optional debug recorder counts a JSONL entry only after writing it. An append
or metadata failure stops that recording session and records a bounded diagnosis;
subsequent GSI/advice calls do no recorder I/O until explicitly started again.
Session directories have unique suffixes. Metadata uses atomic JSON replacement.
If a line succeeds but metadata fails, the line is counted and the previous
metadata remains intact. Its own file-ordering lock remains; GSI/MatchMemory owners
are not held during these writes.

MatchRecords retains its existing bounded flush buffer. Failed flushes now expose
`unconfirmed_lines`, failure count and last error. This is not lossless retry:
gzip append or metadata failure can follow a partial write, so those lines are
unconfirmed rather than declared either durable or all lost. Historical prune
and list behavior is unchanged.

Launcher settings retain edits in RAM after write failure, exposing revision,
acknowledged revision, pending and safe error code/time. A later set/update can
retry the complete settings value. Unique exclusive temporary files use mode
0600 where supported; cleanup is attempted after failure. Existing return values,
default merging and settings schema remain compatible. Only error operation/code
reach the launcher log; configuration values and parser error text do not.

`/diagnostics.recording_health` and the existing user-requested problem report
include these bounded counters. The report preview/redaction/consent flow remains;
UK/EN privacy copy names the aggregates. There is no new automatic upload.

Real-file tests cover blocked destinations, corrupt/invalid serialization,
preservation of previous JSON, temporary cleanup, same-packet census retry,
recorder stop/restart and actual live HTTP responses during recording failure.
This bounds failure retries and retained memory, not operating-system I/O latency.
Replacement is not a power-loss durability guarantee, and recording is still an
optional debugging feature. Raw debugging files remain local and keep the existing
format; they are not included in the problem report.
