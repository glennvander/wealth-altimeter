# Wealth Altimeter

An interactive page that shows US household wealth by percentile as stacks of $100 bills
($1 million = 1.09 m), from the sidewalk to orbit. Built September 2026 as a response to the
2026 update of the "Wealth Inequality in America" video.

Live artifact: https://claude.ai/code/artifact/64c411f5-0ef8-4e70-8bb0-90103c78398d

## Files

- `model.py` — builds `model.json`: per-percentile averages anchored to the Fed's Distributional
  Financial Accounts (Q1 2026), survey thresholds (DQYDJ / SCF 2023), the top-tail split
  (WID shape + Forbes), net-worth headcount bands, and Census income bands from `hinc01.json`.
- `hinc01.json` — Census CPS ASEC table HINC-01, households by income in 2024.
- `altimeter.template.html` — the page, with `/*__DATA__*/` where the model is injected.
- `build.py` — writes `wealth-altimeter.html` (publish this) and `preview.html` (open locally).

## Updating the numbers

1. New Fed quarter: edit the `G` dict in `model.py` (FRED release table, levels in $ millions).
2. New Forbes figures: edit `NAMED` and `MUSK` (the latter is in the template's script header).
3. New survey thresholds: edit `T` in `model.py`.
4. Run `python3 model.py && python3 build.py`, then republish `wealth-altimeter.html`.
