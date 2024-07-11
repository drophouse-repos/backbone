# Load environment variables from .env file if it exists
if (Test-Path -Path .\.env) {
    Get-Content .\.env | ForEach-Object {
        if ($_ -match '^(.*?)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            [System.Environment]::SetEnvironmentVariable($name, $value)
        }
    }
}

# Authenticate with Fly.io
flyctl auth login

# Set secrets on Fly.io
flyctl secrets set `
    OPENAI_KEY=$env:OPENAI_KEY `
    STRIPE_SECRET_KEY=$env:STRIPE_SECRET_KEY `
    STRIPE_SECRET_KEY_TEST=$env:STRIPE_SECRET_KEY_TEST `
    FRONTEND_DOMAIN=$env:FRONTEND_DOMAIN `
    STRIPE_WEBHOOK_SECRET=$env:STRIPE_WEBHOOK_SECRET `
    MONGO_URL=$env:MONGO_URL `
    DATA_API=$env:DATA_API `
    AWS_ACCESS_KEY_ID=$env:AWS_ACCESS_KEY_ID `
    AWS_SECRET_ACCESS_KEY=$env:AWS_SECRET_ACCESS_KEY `
    SENDGRID_API_KEY=$env:SENDGRID_API_KEY `
    PRINTFUL_PRIVATE_TOKEN=$env:PRINTFUL_PRIVATE_TOKEN `
    SESSION_SECRET=$env:SESSION_SECRET `
    STUDENT_FRONTEND_DOMAIN=$env:STUDENT_FRONTEND_DOMAIN `
    JWT_SECRET_KEY=$env:JWT_SECRET_KEY `
    DEMO_FRONTEND_DOMAIN=$env:DEMO_FRONTEND_DOMAIN `
    RECORD_ANALYSIS=$env:RECORD_ANALYSIS `
    DB_ENV=$env:DB_ENV

# Deploy the application
flyctl deploy
