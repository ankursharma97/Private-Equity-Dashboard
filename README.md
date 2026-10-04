# Private Equity Deal Intelligence & Screening Platform

An institutional-style investment screening and deal intelligence platform built using public SEC data, Python, SQL, and Power BI.

The project is designed to simulate a public-market private equity screening workflow — from building an investment universe and analyzing financial performance to comparing potential targets and prioritizing investment opportunities.

## Project Status

**Current Stage:** Day 1 — SEC Universe & Metadata Pipeline Completed

## Objective

Build an interactive investment intelligence platform that can:

- Construct a scalable investment universe from SEC public data
- Analyze multi-year company financial performance
- Screen companies across growth, profitability, cash generation, valuation, and leverage
- Compare potential acquisition targets
- Identify attractive investment opportunities
- Rank and prioritize targets using a configurable investment scoring framework

## Technology Stack

- **Python** — SEC data ingestion, transformation and financial data processing
- **SQL** — Data modeling, analysis and screening logic
- **Power BI** — Interactive investment analytics and visualization
- **SEC EDGAR / XBRL** — Public financial and company data

## Current Data Pipeline

```text
SEC Public Data
       ↓
Company Universe
       ↓
SEC Submission Metadata
       ↓
Financial Data Extraction
       ↓
SQL Data Model
       ↓
Investment Screening
       ↓
Power BI Dashboard
       ↓
Target Comparison & Prioritization