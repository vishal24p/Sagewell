# Debugging Learnings

- For access issues, start with `audit_logs` reason_code, not the
  answer.
- For retrieval issues, compare `candidate_counts` to the access
  decision output.
- For prompt-injection issues, check the regex guard and LLM guard
  verdicts before the answer.
- For citation issues, re-run the access decision on the cited
  document; if it fails, the citation should have been dropped.