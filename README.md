# Parkrun Scraper

This project contains tools to scrape Parkrun results and runner metadata, storing them in a PostgreSQL database. It is designed to be deployed as AWS Lambda functions.

## Handlers

The project provides two entry points (handlers) for AWS Lambda:

1.  **Populate Runners** (`app/handlers/populate_runners.py`): Scrapes recent club results to find new runner IDs and adds them to the database.
2.  **Update Metadata** (`app/handlers/update_metadata.py`): Identifies runners in the database with missing names and scrapes their profiles to update them.

### Lambda Handler Parameters

AWS Lambda functions receive two parameters: `event` and `context`.

#### `event`
The `event` parameter is a Python `dict` that contains the data passed to the function during invocation.
- In `populate_runners.py`, you can pass:
  - `"clubNum"`: The Parkrun club ID to scrape (defaults to 1832).
  - `"clubName"`: The name of the club as it appears in Parkrun results (defaults to "Bellahouston Harriers").
  - **Example**: `{"clubNum": 1234, "clubName": "My Awesome Club"}`
- In `update_metadata.py`, you can pass a `"limit"` key to control how many runners are processed in one run.
  - **Example**: `{"limit": 100}` (defaults to 200 if not provided).

#### `context`
The `context` object provides information about the invocation, function, and execution environment (e.g., time remaining before timeout, function name, memory limit). This project currently uses the standard signature but does not explicitly interact with the `context` properties.

---

## Packaging and Deployment

Because this project uses **Playwright** (requiring browser binaries) and **Psycopg2** (requiring PostgreSQL libraries), the most reliable way to deploy it to AWS Lambda is using a **Docker Container**.

### 1. Build the Docker Image

The project includes a `Dockerfile` optimized for AWS Lambda.

```dockerfile
FROM public.ecr.aws/lambda/python:3.13

# Install system dependencies for Playwright
RUN dnf install -y mesa-libgbm libX11 libXcomposite libXdamage libXext libXfixes libXrandr libXrender libXtst alsa-lib at-spi2-atk at-spi2-core cups-libs dbus-libs expat libdrm libxkbcommon libxshmfence nspr nss nss-util pango && dnf clean all

# Set Playwright to install browsers in a specific location
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV ENV=production

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright browser binaries
RUN playwright install chromium

# Copy application code
COPY app/ ./app/

# The CMD will be overridden by the Lambda configuration for each function
CMD ["app.handlers.populate_runners.lambda_handler"]
```

### 2. Push to Amazon ECR Public

1.  Create a **Public** Amazon ECR repository.
2.  Authenticate your Docker CLI to ECR Public:
    ```bash
    aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/<your-alias>
    ```
3.  Build and tag the image:
    ```bash
    docker build -t parkrun-scraper .
    docker tag parkrun-scraper:latest public.ecr.aws/<your-alias>/parkrun-scraper:latest
    ```
4.  Push to ECR:
    ```bash
    docker push public.ecr.aws/<your-alias>/parkrun-scraper:latest
    ```

### 3. Deploy to AWS Lambda

1.  **Create Function**: In the Lambda console, choose **Create function** -> **Container image**.
2.  **Select Image**: Pick the image from your ECR repository.
3.  **Configure Handlers**:
    - For the "Populate" function, keep the default image CMD or set it to `app.handlers.populate_runners.lambda_handler`.
    - For the "Update Metadata" function, create a second Lambda using the same image but override the **Command** in "Image configuration" to `app.handlers.update_metadata.lambda_handler`.
4.  **Permissions**: Ensure the Lambda has network access to your PostgreSQL database (e.g., via VPC settings).
5.  **Timeout**: Increase the timeout for both functions (e.g., 5-15 minutes) as scraping can take time.

## Scheduling (Daily Runs)

You can use **Amazon EventBridge (CloudWatch Events)** to run these functions on a daily basis:

1.  Open the **EventBridge** console.
2.  Go to **Buses** -> **Rules** -> **Create rule**.
3.  **Define rule detail**: Give it a name (e.g., `daily-parkrun-scrape`).
4.  **Define schedule**:
    - Choose **Schedule**.
    - Use a **Cron expression**: `0 1 * * ? *` (runs daily at 1:00 AM UTC).
5.  **Select targets**:
    - Target 1: **Lambda function** -> Select your "Populate Runners" function.
    - Add another target: **Lambda function** -> Select your "Update Metadata" function.
6.  **Review and create**.

*Note: You may want to stagger them or run them at different times to avoid heavy concurrent DB load.*

## Estimated AWS Costs

Assuming 1024MB RAM for each Lambda and daily execution:

| Service | Estimated Cost (approx.) | Details |
| :--- | :--- | :--- |
| **ECR Storage** | $0.15 / month | ~1.5 GB image at $0.10/GB/month |
| **Lambda Execution** | $0.00 / month | Well within the **Free Tier** (400k GB-s) |
| **Total** | **$0.15 / month** | Excluding DB costs and data transfer |

*If you exceed the Free Tier, Lambda execution for these scripts (totaling ~7,200 GB-s/month) would cost roughly **$0.12/month**.*

## Environment Variables

Configure the following environment variables in the Lambda "Configuration" tab:

| Variable | Description |
| :--- | :--- |
| `DB_NAME` | Name of the PostgreSQL database |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `DB_HOST` | Database host address |
| `DB_PORT` | Database port (default 5432) |
| `ENV` | Set to `production` |

## Continuous Integration and Deployment

This project uses GitHub Actions for automated testing and deployment.

### Automated Testing

On every push and pull request to the `main` branch, the `.github/workflows/python-app.yml` workflow runs all project tests to ensure code quality.

### Automated ECR Deployment

The `.github/workflows/deploy.yml` workflow automatically builds the Docker image and pushes it to Amazon ECR on every push to the `main` branch.

#### AWS Setup Instructions

To enable the deployment workflow using OIDC (OpenID Connect), you need to configure your AWS account and GitHub repository:

1.  **IAM Role Configuration**:
    - Use the provided IAM role: `arn:aws:iam::522341695260:role/GitHubActionECRDeploy`.
    - This role must have a Trust Policy that allows your GitHub repository to assume it via OIDC and should have the **`AmazonElasticContainerRegistryPublicFullAccess`** policy attached (Note: the standard `AmazonEC2ContainerRegistryPowerUser` only covers private registries and is insufficient for ECR Public).

### Troubleshooting IAM & ECR Public (403 Forbidden)

If you encounter a `403 Forbidden` error during the push step, follow these steps in the AWS Console to verify your setup:

#### 1. Verify IAM Role Trust Relationship
1.  Navigate to **IAM** > **Roles** in the AWS Console.
2.  Search for and select your role: `GitHubActionECRDeploy`.
3.  Click the **Trust relationships** tab and then **Edit trust policy**.
4.  Ensure the policy allows your specific GitHub repository. It should look like this:
    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::<YOUR_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringLike": {
              "token.actions.githubusercontent.com:sub": "repo:<YOUR_GITHUB_ORG>/ParkRunScraper:*"
            },
            "StringEquals": {
              "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
            }
          }
        }
      ]
    }
    ```
    *Replace `<YOUR_ACCOUNT_ID>` and `<YOUR_GITHUB_ORG>` with your actual details.*

#### 2. Verify Attached Policies
1.  On the same Role page, click the **Permissions** tab.
2.  Confirm that the **`AmazonElasticContainerRegistryPublicFullAccess`** policy is listed.
3.  If missing, click **Add permissions** > **Attach policies**, search for it, and click **Add permissions**.
4.  **Note**: If you are using a custom policy instead of the recommended full access policy, ensure that any `Resource` ARNs in the policy are updated to match your current repository name.

#### 3. Confirm ECR Public Registry Alias
1.  Navigate to **ECR** > **Public repositories**.
2.  Locate your repository and note its URI. It should follow the format: `public.ecr.aws/<alias>/parkrun-scraper`.
3.  The **`<alias>`** is often a random string (e.g., `d1f2m2x3`).
4.  Ensure your GitHub Secret `ECR_REPOSITORY` is set to exactly `<alias>/parkrun-scraper`.

#### 4. Check for Token Issues
If everything looks correct and it still fails, ensure your GitHub Actions workflow has `id-token: write` permissions (already included in this project's `deploy.yml`).

2.  **Configure GitHub Secrets**:
    - In your GitHub repository, go to **Settings** -> **Secrets and variables** -> **Actions**.
    - Add the following **Repository secrets**:
        - `AWS_REGION`: Must be set to `us-east-1` (required for ECR Public authentication).
        - `AWS_ROLE_TO_ASSUME`: The ARN of the IAM role to assume (e.g., `arn:aws:iam::522341695260:role/GitHubActionECRDeploy`).
        - `ECR_REPOSITORY`: The name of your public ECR repository, including the alias (e.g., `v1a2b3c4/parkrun-scraper`).
    - *Note: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are no longer required as we are using OIDC.*

3.  **Automatic Deployment**:
    Once these secrets are set, any push to the `main` branch will trigger the build and push process using a secure, short-lived OIDC token. You can monitor the progress in the **Actions** tab of your GitHub repository.

## Local Development

1.  Install dependencies: `pip install -r requirements.txt && playwright install chromium`
2.  Create a `.env.local` file with DB credentials.
3.  Run the main script: `python -m app.main`
4.  Run tests: `python -m unittest discover tests -p '*_test.py'`
