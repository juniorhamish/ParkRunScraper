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
RUN dnf install -y \
    atk \
    at-spi2-atk \
    at-spi2-core \
    alsa-lib \
    cups-libs \
    dbus-libs \
    expat \
    fontconfig \
    libdrm \
    libX11 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXfixes \
    libXi \
    libXrandr \
    libXrender \
    libXtst \
    libxkbcommon \
    libxshmfence \
    mesa-libgbm \
    gtk3 \
    nspr \
    nss \
    nss-util \
    pango \
    && dnf clean all

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

### 2. Push to Amazon ECR (Private)

**Note**: AWS Lambda only supports container images from **Private** ECR repositories. It does not currently support ECR Public for Lambda functions.

1.  Create a **Private** Amazon ECR repository in your preferred region.
2.  Authenticate your Docker CLI to your registry:
    ```bash
    aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.<your-region>.amazonaws.com
    ```
3.  Build and tag the image:
    ```bash
    docker build -t parkrun-scraper .
    docker tag parkrun-scraper:latest <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/parkrun-scraper:latest
    ```
4.  Push to ECR:
    ```bash
    docker push <your-account-id>.dkr.ecr.<your-region>.amazonaws.com/parkrun-scraper:latest
    ```

### 3. Deploy to AWS Lambda

This project requires two separate Lambda functions. Both will use the **same Docker image** but will have different entry point configurations.

#### Step A: Create the "Populate Runners" Function
1.  Open the **AWS Lambda Console**.
2.  Click **Create function**.
3.  Select **Container image**.
4.  **Function name**: `parkrun-populate-runners`.
5.  **Container image URI**: Click **Browse ECR** and select your `parkrun-scraper` image with the `latest` tag.
6.  Click **Create function**.

#### Step B: Create the "Update Metadata" Function
1.  Click **Create function** again.
2.  Select **Container image**.
3.  **Function name**: `parkrun-update-metadata`.
4.  **Container image URI**: Select the **same** `latest` image used in Step A.
5.  Expand **Container image overrides**.
6.  In the **Command** field, enter: `app.handlers.update_metadata.lambda_handler` (this overrides the default CMD in the Dockerfile).
7.  Click **Create function**.

#### Step C: Common Configuration (Apply to BOTH functions)
For each of the two functions created above, perform the following configuration:

1.  **Environment Variables**:
    - Go to the **Configuration** tab -> **Environment variables**.
    - Click **Edit** and add:
        - `DB_NAME`: Your database name.
        - `DB_USER`: Your database username.
        - `DB_PASSWORD`: Your database password.
        - `DB_HOST`: Your database host address.
        - `DB_PORT`: `5432`.
        - `ENV`: `production`.
2.  **General Configuration (Timeout & Memory)**:
    - Go to the **Configuration** tab -> **General configuration**.
    - Click **Edit**.
    - **Memory**: Set to at least `2048 MB` (Playwright/Chromium are memory-intensive, especially in a container).
    - **Timeout**: Set to `10 minutes` (600 seconds) or more. Scraping multiple pages takes time and can be hit by network delays.
3.  **VPC / Network Access**:
    - If your PostgreSQL database is in a VPC (e.g., RDS) and not publicly accessible, go to **Configuration** -> **VPC**.
    - Click **Edit** and select the VPC, subnets, and security groups that allow the Lambda to reach your database.

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
    - This role must have a Trust Policy that allows your GitHub repository to assume it via OIDC.
    - It should have the **`AmazonEC2ContainerRegistryPowerUser`** policy attached (Standard for private registries).
    - It also needs permission to update and verify Lambda function code. You should attach a custom policy with the following actions:
        - **`lambda:UpdateFunctionCode`**
        - **`lambda:GetFunction`**
        - **`lambda:GetFunctionConfiguration`**
    - These permissions should be scoped to your specific Lambda functions for best security practices.

2.  **Lambda Execution Role Permissions**:
    - Each Lambda function has an **Execution Role** (configured under the **Configuration** -> **Permissions** tab).
    - Because the functions use a container image from ECR, this execution role **must** have permission to pull the image.
    - Attach the following permissions to the Lambda Execution Role:
        - `ecr:BatchCheckLayerAvailability`
        - `ecr:GetDownloadUrlForLayer`
        - `ecr:BatchGetImage`
    - Alternatively, you can attach the managed policy `AmazonEC2ContainerRegistryReadOnly` to the execution role.

### Troubleshooting IAM & ECR (403 Forbidden)

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
2.  Confirm that the **`AmazonEC2ContainerRegistryPowerUser`** policy is listed.
3.  If missing, click **Add permissions** > **Attach policies**, search for it, and click **Add permissions**.
4.  **Note**: If you are using a custom policy instead of the recommended PowerUser policy, ensure that any `Resource` ARNs in the policy are updated to match your current repository name.

#### 3. Confirm ECR Registry URI
1.  Navigate to **ECR** > **Repositories**.
2.  Locate your repository and note its URI. It should follow the format: `<account-id>.dkr.ecr.<region>.amazonaws.com/parkrun-scraper`.
3.  Ensure your GitHub Secret `ECR_REPOSITORY` is set to exactly `parkrun-scraper` (or your chosen repository name).

#### 4. Check for Token Issues
If everything looks correct and it still fails, ensure your GitHub Actions workflow has `id-token: write` permissions (already included in this project's `deploy.yml`).

3.  **Configure GitHub Secrets**:
    - In your GitHub repository, go to **Settings** -> **Secrets and variables** -> **Actions**.
    - Add the following **Repository secrets**:
        - `AWS_REGION`: The AWS region where your ECR repository and Lambda are located (e.g., `eu-west-1`).
        - `AWS_ROLE_TO_ASSUME`: The ARN of the IAM role to assume (e.g., `arn:aws:iam::522341695260:role/GitHubActionECRDeploy`).
        - `ECR_REPOSITORY`: The name of your ECR repository (e.g., `parkrun-scraper`).
        - `LAMBDA_POPULATE_NAME`: The name of your "Populate Runners" Lambda function (e.g., `parkrun-populate-runners`).
        - `LAMBDA_UPDATE_NAME`: The name of your "Update Metadata" Lambda function (e.g., `parkrun-update-metadata`).
    - *Note: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are no longer required as we are using OIDC.*

4.  **Automatic Deployment**:
    Once these secrets are set, any push to the `main` branch will trigger the build and push process using a secure, short-lived OIDC token. You can monitor the progress in the **Actions** tab of your GitHub repository.

## Local Development

1.  Install dependencies: `pip install -r requirements.txt && playwright install chromium`
2.  Create a `.env.local` file with DB credentials.
3.  Run the main script: `python -m app.main`
4.  Run tests: `python -m unittest discover tests -p '*_test.py'`
