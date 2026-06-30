# CFM-ID Full Runtime Extrapolation

This estimate uses the observed 10-query native CFM-ID subset timings to explain why full CASMI candidate ranking remains a long-running job.

| basis                                             |   seconds_per_candidate |   supported_queries |   unsupported_queries |   total_supported_candidate_rows |   estimated_single_worker_seconds |   estimated_single_worker_hours |   estimated_16_worker_hours_ideal | guardrail                                                                                                                |
|:--------------------------------------------------|------------------------:|--------------------:|----------------------:|---------------------------------:|----------------------------------:|--------------------------------:|----------------------------------:|:-------------------------------------------------------------------------------------------------------------------------|
| mean_seconds_per_candidate_from_10_query_subset   |                 8.43779 |                 170 |                    59 |                          1062950 |                       8.96895e+06 |                         2491.37 |                           155.711 | Back-of-envelope estimate only; CFM-ID runtime varies by molecule and this does not include [M+Na]+ unsupported queries. |
| median_seconds_per_candidate_from_10_query_subset |                 6.71049 |                 170 |                    59 |                          1062950 |                       7.13292e+06 |                         1981.37 |                           123.835 | Back-of-envelope estimate only; CFM-ID runtime varies by molecule and this does not include [M+Na]+ unsupported queries. |

The estimate is not a replacement for a full result. It supports the current reporting decision: full native CFM-ID CASMI Top-k metrics remain unavailable, while the candidate-limited subset demonstrates the native path.
