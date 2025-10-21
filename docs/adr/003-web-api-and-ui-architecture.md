# ADR 003: Web API and UI Architecture

## Status

Proposed

## Context

The existing Conversational Email Assistant is a command-line application. To broaden its accessibility and provide a more user-friendly experience, there is a requirement to:
1.  Expose the core LangGraph assistant functionality via a public, secure HTTP API.
2.  Build a web-based user interface that consumes this API.
3.  Ensure both components are scalable, maintainable, and deployable to a cloud environment.

## Decision

We will adopt a decoupled, service-oriented architecture consisting of two new, distinct services:

1.  **FastAPI API Service:** A Python-based API wrapper around the existing LangGraph assistant.
    *   **Framework:** FastAPI will be used for its lightweight nature and ease of integration with our existing Python codebase.
    *   **Containerization:** The service will be containerized using Docker for consistent deployments.
    *   **Endpoints:** It will include a minimal `/healthz` endpoint for health checks and API endpoints to interact with the LangGraph agent.
    *   **Deployment:** It will be deployed as a Google Cloud Run service.

2.  **Django Web UI Service:** A Python-based web application to serve as the user interface.
    *   **Framework:** Django will be used for its robust feature set, including its templating engine and static file management, which are well-suited for building a user-facing web application.
    *   **Static Files:** Whitenoise will be used to serve static files (CSS, JS) directly from the Django application, simplifying deployment.
    *   **API Consumption:** The UI will communicate with the FastAPI API via HTTPS, with Cross-Origin Resource Sharing (CORS) enabled on the API to allow requests from the UI's domain.
    *   **Containerization:** This service will also be containerized using Docker.
    *   **Deployment:** It will be deployed as a separate Google Cloud Run service.

## Consequences

### Positive:
*   **Decoupling:** The UI and API are separated, allowing them to be developed, deployed, and scaled independently.
*   **Scalability:** Google Cloud Run provides serverless, auto-scaling infrastructure, which is cost-effective and handles variable traffic loads well.
*   **Accessibility:** The web UI makes the assistant accessible to non-technical users. The API allows for potential future integrations with other services.
*   **Maintainability:** The separation of concerns makes the overall system easier to understand and maintain.

### Negative:
*   **Increased Complexity:** The project now involves two new services, containerization, and cloud deployment configurations, increasing the overall complexity.
*   **New Dependencies:** We are introducing FastAPI, Django, Docker, and Google Cloud Run as new core technologies.
*   **Operational Overhead:** We will need to manage CI/CD pipelines, monitoring, and logging for two services instead of one.
*   **Security Considerations:** The public-facing API introduces new security concerns, such as authentication, authorization, and CORS, which must be addressed.