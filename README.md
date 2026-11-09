# Banking Enterprise Data Lakehouse Simulator

> **Synthetic demo data only — not for production banking data.**
> Personal portfolio project. Not an official BNI system, not connected to any bank infrastructure.

A locally runnable banking data lakehouse simulator that demonstrates governed multi-unit data onboarding, Medallion Architecture processing (Landing → Bronze → Silver → Gold), metadata management, data quality, lineage, and time-bound access to curated data products.

## Docs

- [Product Requirements (PRD)](docs/PRD.md)
- [Tech stack architecture](docs/architecture.mmd) (Mermaid)
- [Metadata ERD](docs/erd.mmd) (Mermaid)

## Stack

Streamlit · FastAPI · PostgreSQL · DuckDB + PyArrow + Pandas · Parquet · Docker Compose · Pytest · Plotly

## Status

Work in progress. Being built milestone by milestone (see PRD section 19).
