# Process Email Workflow Implementation

## Overview

This implementation provides a complete email processing workflow for the Job Hub application that handles deduplication, database operations, and intent-based processing.

## Core Function: `process_email`

The main function `process_email` in `services/db_operations.py` implements the following workflow:

### 1. Deduplication

- Checks if `raw_email_id` already exists in the `emails` table
- If found, returns early with status "duplicate"
- Prevents reprocessing of the same email

### 2. Raw Email Storage

- Inserts a complete record into the `emails` table for auditing
- Stores all email metadata (sender, recipient, subject, body, timestamps)
- Includes LLM confidence score if available

### 3. Intent-Based Processing

#### NEW_APPLICATION Intent

- Calls `handle_new_application()`
- Creates a new record in `job_applications` table
- Links the raw email to the new application via `application_id`
- Sets timestamps for `applied_date`, `last_updated_at`, and `last_email_received_at`

#### APPLICATION_EVENT Intent

- Calls `handle_application_event()`
- Looks up existing application by:
  1. `parsed.application_id` (if provided)
  2. Fallback to matching by `user_id + company + role`
- Creates record in `application_events` table
- Updates only changed fields on the existing application
- Links the raw email to the matched application

#### GENERAL Intent

- No further processing required
- Email is stored for auditing but no application/event actions taken

## Key Features

### Transaction Safety

- Each handler (`handle_new_application`, `handle_application_event`) is wrapped with retry logic
- Exponential backoff for failed attempts (up to 3 retries by default)
- Proper error handling and logging

### Application Matching

- Enhanced `application_matcher.py` with exact and case-insensitive matching
- Supports lookup by user, company, role, and optional location
- Utility functions for updating application fields

### Database Schema Compliance

- Matches the provided DATABASE_SCHEMA.sql structure
- Proper foreign key relationships between tables
- Uses UUID primary keys and enum types as defined

## Integration Points

### API Endpoint

- Updated `/parse-email` endpoint in `routes/parse.py`
- Now uses `process_email` instead of legacy functions
- Handles all response scenarios (new applications, events, duplicates)

### Error Handling

- Custom `DatabaseOperationError` exception for database-related failures
- Comprehensive logging throughout the workflow
- Graceful handling of missing applications for events

## Backward Compatibility

The legacy `insert_job_application_with_retry` function is preserved but deprecated, calling the new `process_email` workflow internally.

## Testing

A test script `test_process_email.py` is provided to verify all workflow scenarios:

- New application creation
- Application event processing
- Duplicate email handling
- General email processing

## Database Operations

### Tables Updated

- `emails`: Raw email storage with parsing metadata
- `job_applications`: Application records with status tracking
- `application_events`: Event history linked to applications

### Key Fields

- `last_email_received_at`: Tracks most recent email activity
- `last_updated_at`: Tracks any application changes
- `application_id`: Links between emails and applications
- `external_email_id`: Used for deduplication

This implementation provides a robust, scalable foundation for email-based job application tracking with proper separation of concerns and comprehensive error handling.
