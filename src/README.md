# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- Publish school announcements with optional start dates and required expiration dates

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| GET    | `/announcements`                                                  | Get announcements that are currently visible (public)               |
| GET    | `/announcements/all?teacher_username=...`                         | Get every announcement, including scheduled and expired ones        |
| POST   | `/announcements?teacher_username=...`                             | Create an announcement                                              |
| PUT    | `/announcements/{announcement_id}?teacher_username=...`           | Update an announcement                                              |
| DELETE | `/announcements/{announcement_id}?teacher_username=...`           | Delete an announcement                                              |

Announcement create and update requests take a JSON body:

```json
{
  "title": "Spring Concert Rehearsal",
  "message": "Band members meet in the auditorium at 3:00 PM.",
  "start_date": "2025-04-01T08:00:00Z",
  "expiration_date": "2025-04-15T17:00:00Z"
}
```

`start_date` is optional (the announcement shows immediately when omitted) and
`expiration_date` is required. All announcement management endpoints require the
`teacher_username` of a signed in teacher.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

3. **Announcements** - Uses a generated id as identifier:
   - Title
   - Message
   - Start date (optional)
   - Expiration date (required)
   - Author username

All data is stored in memory, which means data will be reset when the server restarts.
