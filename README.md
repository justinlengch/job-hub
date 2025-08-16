# Job Hub

A comprehensive job application tracking system that automatically parses emails and organizes your job search process.

## Overview

Job Hub is a full-stack application that helps job seekers manage their applications by automatically parsing job-related emails and tracking application status through an intuitive dashboard. The system integrates with Gmail to monitor job application emails and uses AI to extract relevant information automatically.

## Features

### 🤖 Automated Email Processing
- **Gmail Integration**: Automatically monitors your Gmail for job-related emails
- **AI-Powered Parsing**: Uses LLM to extract company names, roles, status updates, and other relevant information
- **Smart Categorization**: Automatically creates labels and filters in Gmail for job application emails

### 📊 Application Tracking
- **Status Management**: Track applications through multiple stages (Applied, Assessment, Interview, Rejected, Offered, etc.)
- **Timeline View**: Visual timeline of all application events and communications
- **Dashboard Analytics**: Overview of application statistics and trends

### 💼 Comprehensive Data Management
- **Application Details**: Store company info, role details, salary ranges, locations, and notes
- **Event Tracking**: Log interviews, assessments, offers, and other application milestones
- **Email History**: Maintain a complete record of all job-related communications

## Tech Stack

### Frontend (Web App)
- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** + **shadcn/ui** for styling
- **React Router** for navigation
- **TanStack Query** for data fetching
- **React Hook Form** + **Zod** for form handling

### Backend (API)
- **FastAPI** with Python 3.13
- **SQLModel** for database ORM
- **Supabase** for database and authentication
- **Google Gmail API** for email integration
- **Google Generative AI** for email parsing
- **Pydantic** for data validation

### Infrastructure
- **Turborepo** monorepo setup
- **pnpm** for package management
- **Docker** containerization
- **Heroku** deployment

## Project Structure

```
job-hub/
├── apps/
│   ├── web/           # React frontend application
│   └── backend/       # FastAPI backend service
├── DATABASE_SCHEMA.sql # PostgreSQL database schema
├── package.json       # Root workspace configuration
├── turbo.json        # Turborepo configuration
└── heroku.yml        # Heroku deployment config
```
