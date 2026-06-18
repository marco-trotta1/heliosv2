# USDA LIRF Maize 2008-2011 Acquisition Audit

Date: 2026-06-17

## Finding

The 2008-2011 Colorado LIRF maize dataset is directly available from Ag Data Commons/Figshare and should be treated as the next public-data acquisition target, not silently blended into the 2012-2013 candidate evaluation.

## Evidence Checked

- 2012-2013 API record: `https://api.figshare.com/v2/articles/24662391`
  - The record references a previous Ag Data Commons dataset named `USDA-ARS Colorado Maize Water Productivity Dataset 2008-2011`.
  - Related article DOI: `10.1016/j.dib.2018.10.140`.
- Figshare article search for `USDA-ARS Colorado Maize Water Productivity Dataset 2008-2011`
  - Found article id `24660372`.
  - Public page: `https://agdatacommons.nal.usda.gov/articles/dataset/USDA-ARS_Colorado_Maize_Water_Productivity_Dataset_2008-2011/24660372`
  - Dataset DOI: `10.15482/USDA.ADC/1254006`.
  - Related Springer DOI: `10.1007/s00271-017-0537-9`.
- 2008-2011 API record: `https://api.figshare.com/v2/articles/24660372`
  - Files are directly downloadable.
  - Maize files: `LIRF Maize 2008 r1_0.xlsx`, `LIRF Maize 2009 r1_0.xlsx`, `LIRF Maize 2010 r1_0.xlsx`, `LIRF Maize 2011 r1_0.xlsx`.
  - Weather files: `LIRF Weather 2008.xlsx`, `LIRF Weather 2009.xlsx`, `LIRF Weather 2010.xlsx`, `LIRF Weather 2011.xlsx`.
  - Supporting files: `LIRF Soils.xlsx`, `DataDictionary r1.xlsx`, `LIRF Methodology r1.pdf`, `LIRF Photo Log.pdf`.
  - License: U.S. Public Domain.

## Current Repo State

`helios/data/public_datasets.json` currently registers `usda_lirf_2012_2013`, but not `usda_lirf_2008_2011`. The current training/evaluation artifacts therefore use only the already-ingested 2012-2013 maize data.

## Next Action

Add a separate registry entry and downloader/parser path for `usda_lirf_2008_2011`, with MD5 gates from article `24660372`. Do not merge these files into training until their schema is parsed into the same source-aware wide format and evaluated through the same leakage-free gates used by `artifacts/maize_baseline_eval.json`.
