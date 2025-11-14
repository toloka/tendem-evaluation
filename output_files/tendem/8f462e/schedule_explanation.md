**Summary (important note on client request + working assumption):** The original request contains internal inconsistencies: with an 8‑week schedule, one OFF week per Account Manager (AM), and a limit of one presentation per week, each AM has only 7 available presentation slots, yet “every segment once” requires 8. In addition, “exactly 3 Enterprise + 4 SMB” totals 7, which conflicts with covering 8 distinct segments. To deliver a feasible, fair plan that preserves the 8‑week duration, OFF weeks, and one‑per‑week cadence, we explicitly adopt this assumption: each AM presents to exactly 3 Enterprise and 4 SMB segments (7 total) and has exactly 1 OFF week. Under this assumption, not every AM covers all 8 segments individually; however, all 8 segments are covered collectively across the team, and all special constraints remain honored (B→EF W1; C→ST W6; D→EH W2; F→EM W5; A OFF W4; E OFF W7).

## Schedule optimization and constraints satisfaction (final, no double‑presentations)

### Why this approach was chosen
- **Feasible within 8 weeks + OFF week:** One presentation per active week (7 weeks) + 1 OFF week per AM fits exactly 7 total presentations (3 Enterprise + 4 SMB) with no double‑booking.
- **Operationally realistic cadence:** Preserves training/conference time and weekly pacing, avoiding overloading any week.
- **Transparency about trade‑off:** Individual “every segment once” is not possible with 7 available presentation slots; we document this explicitly and ensure collective coverage across the team.

### What this means in practice
- **Per‑manager cadence:** Each AM has exactly **1 OFF week** and **7 single‑presentation weeks**.
- **Per‑manager coverage:** Exactly **3 Enterprise + 4 SMB** segments (7 total) per AM; no AM exceeds one presentation in any week.
- **Collective coverage:** Across all AMs, **all 8 client segments (EF, EH, EM, ER, ST, SS, SE, SC)** are covered during the 8‑week period.
- **Special constraints honored:** B→EF (Week 1); C→ST (Week 6); D→EH (Week 2); F→EM (Week 5); A OFF (Week 4); E OFF (Week 7).

### Verification summary (high level)
- Each week includes exactly **one OFF** manager and **seven** presentations.
- Each AM: **OFF=1**, **Enterprise=3**, **SMB=4**, no more than **one presentation per week**.
- All stated **special constraints** are satisfied.

### Files included and how to use them
- **presentation_schedule.md / .csv** — Week × AM matrix of assignments (one presentation per AM per active week; OFF marked accordingly).
- **weekly_off_summary.csv** — OFF manager by week (reference for training/conference tracking).
- **weekly_segments_summary.csv** — Per‑week list of segments and counts, confirming collective coverage of all 8 segments across the 8‑week period.
