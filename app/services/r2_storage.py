import os
import boto3


def upload_markdown(content: str, key: str) -> str:
    """Upload markdown string to Cloudflare R2. Returns the public URL."""
    endpoint = os.getenv(
        "R2_ENDPOINT",
        "https://f6eeda1379f4bcdf2b7b6dad559cd8a7.r2.cloudflarestorage.com",
    )
    bucket = os.getenv("R2_BUCKET", "quantum-bytes")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    public_url = os.getenv("R2_PUBLIC_URL", "")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType="text/markdown",
    )

    if public_url:
        return f"{public_url.rstrip('/')}/{key}"
    return f"{endpoint.rstrip('/')}/{bucket}/{key}"
