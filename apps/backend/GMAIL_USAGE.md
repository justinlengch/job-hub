# Gmail Integration Example

This example demonstrates how to use the Gmail service to create labels and filters for job application emails.

## Basic Usage

```python
from app.services.gmail import gmail_service

# 1. Initialize Gmail client with user credentials
user_credentials = {
    "access_token": "your_access_token",
    "refresh_token": "your_refresh_token"
}

# Create Gmail client
success = gmail_service.create_gmail_client(user_credentials)
if not success:
    print("Failed to authenticate with Gmail")
    exit()

# 2. Set up complete job application labeling (creates label + filter)
label_id = gmail_service.setup_job_application_labeling("Job Applications")
if label_id:
    print(f"Successfully set up job application labeling with label ID: {label_id}")
else:
    print("Failed to set up job application labeling")
```

## Step-by-step Usage

```python
# 1. Create Gmail client
gmail_service.create_gmail_client(user_credentials)

# 2. Create or get label
label_id = gmail_service.get_or_create_label("Job Applications")

# 3. Create filter for the label
filter_success = gmail_service.create_job_application_filter(label_id)

# 4. List existing filters (optional)
filters = gmail_service.list_existing_filters()
print(f"User has {len(filters)} filters")

# 5. Delete a filter (optional)
gmail_service.delete_filter("filter_id_to_delete")
```

## API Endpoints

### Setup Filter and Label

```bash
POST /api/gmail/setup-filter
Content-Type: application/json
Authorization: Bearer <your-jwt-token>

{
  "credentials": {
    "access_token": "your_access_token",
    "refresh_token": "your_refresh_token"
  },
  "label_name": "Job Applications"
}
```

### Test Gmail Connection

```bash
POST /api/gmail/test-connection
Content-Type: application/json
Authorization: Bearer <your-jwt-token>

{
  "access_token": "your_access_token",
  "refresh_token": "your_refresh_token"
}
```

### List Existing Filters

```bash
GET /api/gmail/filters
Authorization: Bearer <your-jwt-token>
```

### Delete a Filter

```bash
DELETE /api/gmail/filters/{filter_id}
Authorization: Bearer <your-jwt-token>
```

## Filter Criteria

The job application filter automatically labels emails that match these criteria:

**Subject Keywords:**

- resume, CV, application, interview, position, opportunity
- hiring, recruitment, job, career, candidate, applicant
- offer, screening, assessment

**Application Status & Communication:**

- "application received", "we received your application", "confirmation of your application"
- "thank you for applying", "thank you for your application", "thank you for your interest"
- "your application to", "application submitted for"

**Interview Related:**

- "interview invitation", "schedule interview", "invitation to interview"
- "next steps", "move forward", "follow-up"

**Job Offers & Updates:**

- "job offer", "offer letter", "pleased to inform", "status update", "application status"

**Recruiter Keywords:**

- "talent partner", "technical recruiter", "sourcing recruiter", "founding engineer"
- "quick call", SWE, SDE, "be a good fit"
- "job application", "Job opportunity", "Career opportunity"

**Sender Domains:**

- @linkedin.com, @indeed.com, @glassdoor.com
- @workday.com, @greenhouse.io, @lever.co
- @bamboohr.com, @jobvite.com, @smartrecruiters.com
- noreply, recruiting, talent, hr, careers

**Attachments:**

- PDF, DOC, DOCX files

**Exclusions:**

- Spam, advertisements, promotions, sales emails

## Environment Variables

Make sure to set these in your `.env` file:

```
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_PROJECT_ID=your_google_project_id
```

## Next Steps

This implementation provides the foundation for:

1. Real-time email monitoring with Pub/Sub
2. Automatic email parsing with LLM
3. Integration with the existing `/parse-email` endpoint
4. Storing parsed data in Supabase

See `gmail_integration.md` for the complete workflow implementation.
