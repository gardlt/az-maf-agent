# MCP 50-query test results

**Date:** 2026-10-19  
**Environment:** Dev Container App  
**Endpoint:** `https://ca-maf-agent-dev-eus2-01.kindisland-49d1cad2.eastus2.azurecontainerapps.io`

## Result

The authenticated movie MCP test completed successfully:

- **50/50 queries returned HTTP 200**
- **10 sessions** were used, with 5 queries per session
- No query failures occurred
- All returned records came from TMDB

## Query results

| Query range | Catalog IDs | Result |
| --- | --- | --- |
| 1–10 | `tmdb_11`, `tmdb_1891`, `tmdb_603`, `tmdb_550`, `tmdb_680`, `tmdb_13`, `tmdb_155`, `tmdb_27205`, `tmdb_157336`, `tmdb_278` | 10/10 HTTP 200 |
| 11–20 | Same sequence | 10/10 HTTP 200 |
| 21–30 | Same sequence | 10/10 HTTP 200 |
| 31–40 | Same sequence | 10/10 HTTP 200 |
| 41–50 | Same sequence | 10/10 HTTP 200 |

The movies returned were:

1. Star Wars
2. The Empire Strikes Back
3. The Matrix
4. Fight Club
5. Pulp Fiction
6. Forrest Gump
7. The Dark Knight
8. Inception
9. Interstellar
10. The Shawshank Redemption

## Session budget observation

A separate initial run attempted all 50 queries in one session. The first 8 queries returned HTTP 200; queries 9–50 returned HTTP 409 with `{"error":"tool_budget"}`. This confirms the per-session read budget is enforced. The final run used fresh sessions and completed all 50 queries successfully.
