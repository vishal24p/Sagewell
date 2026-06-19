# Evaluation Learnings

- V1 has two evaluation systems, not one. RAGAS does not replace the
  RBAC Access Outcome Suite.
- RBAC cases test the access decision function, not the answer
  string.
- RAGAS cases test quality metrics, not access outcomes.
- The release gate blocks on RBAC regression.