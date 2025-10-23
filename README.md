# Conversational Email Assistant

This project is a conversational email assistant that helps you draft replies to your emails. You can interact with it in a conversational manner, providing it with an email (either as text or a PDF), and it will help you extract key information, summarize the content, and generate a draft reply. You can then refine the draft with further instructions.

## Features

*   **Conversational Interface**: Interact with the assistant using natural language in a CLI.
*   **Multi-format Input**: Process emails from raw text or by loading a PDF file.
*   **Information Extraction**: Automatically identifies and extracts key information like sender, receiver, and subject.
*   **Summarization**: Provides a concise summary of the email content.
*   **Draft Generation**: Generates an initial draft reply based on the email's context.
*   **Iterative Refinement**: Modify the draft with commands like "make it more formal" or "add a sentence about the deadline".
*   **Tone Selection**: Specify a tone (e.g., formal, casual) for the generated draft.
*   **Save Drafts**: Save your final draft to a local file or to an AWS S3 bucket.

## Architecture

For a detailed explanation of the project's components, design principles, and technical decisions, please see the [Architectural Plan](docs/Architectural_Plan.md).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/eassistant.git
    cd eassistant
    ```

2.  **Install package and dependencies:**
    ```bash
    pip install .
    ```

3.  **Configure AWS Credentials:**
    The assistant uses AWS Bedrock for its language model capabilities and can use AWS S3 for storage. You need to configure your AWS credentials so the application can access these services. The recommended way is to set up environment variables:
    ```bash
    export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY"
    export AWS_SESSION_TOKEN="YOUR_SESSION_TOKEN" # Optional, for temporary credentials
    ```
    Alternatively, you can configure a credentials file at `~/.aws/credentials`. Refer to the [Boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html) for more details.

4.  **Configure the Application:**
    The main configuration is in `config/default.yaml`. You may need to adjust the settings based on your environment. See the Configuration section below for more details.

## Usage

To start the interactive shell, run:
```bash
eassistant
```
You can then start a conversation. For example:
> **You:** Hi, I need help with an email.
>
> **Assistant:** Of course. Please paste the email text or provide a path to a file.
>
> **You:** load ./tests/fixtures/example.txt
>
> **Assistant:** (Processes the email and displays summary)
>
> **You:** Please draft a professional reply.
>
> **Assistant:** (Generates a draft)
>
> **You:** Looks good. Save it to the cloud.
>
> **Assistant:** Draft saved to S3.

To exit the shell, type `exit` or `quit`.

## Deployment

This project is designed to be deployed as two separate services on Google Cloud Run: a FastAPI backend (`api`) and a Django frontend (`ui`).

### Google Cloud Run

Each service (`services/api` and `services/ui`) contains a `cloudbuild.yaml` file that defines the build and deployment steps for Google Cloud Build.

**Prerequisites:**

1.  A Google Cloud Project with the Cloud Build and Cloud Run APIs enabled.
2.  The `gcloud` command-line tool installed and authenticated.
3.  Your GCP Project ID configured (e.g., `gcloud config set project YOUR_PROJECT_ID`).
4.  Permissions for your Cloud Build service account to deploy to Cloud Run.

**Deployment Steps:**

To deploy a service, navigate to its directory and submit the build:

```bash
# To deploy the API
cd services/api
gcloud builds submit --config cloudbuild.yaml .

# To deploy the UI
cd services/ui
gcloud builds submit --config cloudbuild.yaml .
```

This command will instruct Cloud Build to:
1.  Build the Docker image for the service.
2.  Push the image to Google Container Registry (GCR).
3.  Deploy the new image to the corresponding Cloud Run service.

### Environment Variables

When deploying to Cloud Run, you must configure the following environment variables.

**API Service (`eassistant-api`):**

*   `AWS_ACCESS_KEY_ID`: Your AWS access key.
*   `AWS_SECRET_ACCESS_KEY`: Your AWS secret key.
*   `AWS_SESSION_TOKEN` (Optional): For temporary credentials.
*   `MODEL_ID`: The AWS Bedrock model ID (e.g., `anthropic.claude-3-sonnet-20240229-v1:0`).
*   `S3_BUCKET_NAME`: The name of the S3 bucket for cloud storage.
*   `REGION_NAME`: The AWS region for Bedrock and S3 (e.g., `us-east-1`).

**UI Service (`eassistant-ui`):**

*   `SECRET_KEY`: A long, random string for Django's cryptographic signing.
*   `API_URL`: The full URL of the deployed API service (e.g., `https://eassistant-api-xxxxxxxxxx-uc.a.run.app`).
*   `DJANGO_DEBUG`: Set to `False` in production.
*   `DJANGO_ALLOWED_HOSTS`: The hostname of your UI service (e.g., `eassistant-ui-xxxxxxxxxx-uc.a.run.app`).

You can set these during deployment using the `--set-env-vars` flag in `cloudbuild.yaml` or by configuring them in the Google Cloud Console.

## Configuration

The application is configured via the `config/default.yaml` file.

```yaml
# config/default.yaml

# The ID of the model to use for the LLM service on AWS Bedrock
# Example: "anthropic.claude-3-sonnet-20240229-v1:0"
model_id: "anthropic.claude-3-sonnet-20240229-v1:0"

# The name of the S3 bucket to use for cloud storage.
# This is only required if you intend to use the "save to cloud" feature.
s3_bucket_name: "your-s3-bucket-name"

# The AWS region where your Bedrock and S3 services are located.
region_name: "eu-west-1"
```

### Configuration Details:

*   `model_id`: Specifies which AWS Bedrock model to use. The default is Claude 3 Sonnet. Ensure the model is enabled for your AWS account in the specified `region_name`.
*   `s3_bucket_name`: If you want to save drafts to S3, provide the name of your bucket here. The AWS credentials you configured must have `s3:PutObject` permissions for this bucket.
*   `region_name`: The AWS region for both Bedrock and S3. Make sure this is set correctly.