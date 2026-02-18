# Bug Bounty Writeups Aggregator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a daily-updated writeup aggregator for PortSwigger, Medium, and HackerOne with Telegram/Discord notifications and a responsive web reader.

**Architecture:** Python scraper jobs run daily from GitHub Actions, normalize records, and upsert into Supabase Postgres. React frontend reads via API and provides source/year/month filters, sorted by newest. Optional FastAPI backend serves read endpoints and health checks.

**Tech Stack:** Python 3.12, FastAPI, requests, BeautifulSoup, Supabase Postgres (SQL + RLS), React + Vite + TypeScript, Mantine, TanStack Query v5.

---

### Task 1: Data contracts and tests
- Create shared writeup model and parser tests.
- Cover RSS parsing, HackerOne HTML extraction fallback, date filtering (>= 2025-01-01), dedupe keys.

### Task 2: Scraper and notifications
- Implement source fetchers and normalization pipeline.
- Implement Supabase upsert with unique URL constraint.
- Add Telegram/Discord notifier functions.

### Task 3: API and schema
- Add FastAPI endpoint for filtered list and health check.
- Add Supabase SQL schema, indexes, RLS policies, retention SQL.

### Task 4: Frontend reader
- Build responsive UI with Mantine + TanStack Query.
- Add filters: source/year/month and date-sorted list.

### Task 5: Automation and docs
- Add GitHub Actions daily workflow.
- Write environment setup and free-tier deployment docs.
- Verify with test/build commands.
