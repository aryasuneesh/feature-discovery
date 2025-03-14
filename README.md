# Feature Discovery Agent

A backend service that helps users discover and learn about product features based on their context and behavior.

## Overview

This system tracks user interactions with an application, analyzes their context, and recommends relevant features they might not be aware of. It also provides tutorials and automation capabilities to help users learn and adopt new features.

## Core Components

- **Context Analysis**: Captures user's current application state to understand what they're trying to accomplish
- **Feature Recommendation**: Suggests relevant features based on user context and history
- **Tutorials**: Provides step-by-step guides for using recommended features
- **Automation**: Offers to automate repetitive tasks when possible
- **Analytics**: Tracks feature discovery metrics and generates insights

## Technical Stack

- **FastAPI**: REST API framework with automatic validation and documentation
- **SQLAlchemy**: ORM for database interactions and model definitions
- **Pydantic**: Data validation and serialization
- **SQLite**: Default database (configurable to other databases)

## Data Models

- **Users**: Stores user information and tracks discovery progress
- **Features**: Catalogs available features with metadata
- **Interactions**: Records how users engage with features
- **Contexts**: Captures user's application state for analysis

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```
   poetry install
   ```
3. Set up environment variables (or use defaults):
   ```
   OPENA_API_KEY=<api_key>
   ```
4. Run the application:
   ```
   poetry run uvicorn app.main:app --reload
   ```
5. Access the API documentation at http://localhost:8000/docs

## API Endpoints

- `/context`: Submit current user context for analysis
- `/recommend`: Get feature recommendations
- `/tutorial`: Request tutorials for specific features
- `/automate`: Request automation for supported tasks
- `/feedback`: Submit ratings and comments
- `/insights`: Get analytics on feature discovery

## Development

The project uses Poetry for dependency management and follows standard Python project structure.
