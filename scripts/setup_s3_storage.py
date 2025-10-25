"""
Setup S3 storage block for meal planner result storage.

Creates a Prefect S3Bucket block without credentials (uses AWS environment credentials).

Usage:
    python scripts/setup_s3_storage.py

The script will prompt for the bucket name or you can pass it as an argument:
    python scripts/setup_s3_storage.py my-meal-planner-results
"""

import sys
from prefect_aws.s3 import S3Bucket


def main():
    # Get bucket name from command line or prompt
    if len(sys.argv) > 1:
        bucket_name = sys.argv[1]
    else:
        bucket_name = input("Enter S3 bucket name: ").strip()

    if not bucket_name:
        print("Error: Bucket name is required")
        sys.exit(1)

    # Remove s3:// prefix if provided
    bucket_name = bucket_name.replace("s3://", "")

    block_name = "meal-planner-results"

    print(f"\nCreating S3Bucket block '{block_name}' for bucket '{bucket_name}'...")

    # Create and save S3 bucket block without credentials
    # Will use AWS credentials from environment (CLI, IAM role, etc.)
    s3_block = S3Bucket(bucket_name=bucket_name)
    s3_block.save(block_name, overwrite=True)

    print(f"✓ Created S3Bucket block: {block_name}")
    print(f"  - Block slug: 's3-bucket/{block_name}'")
    print(f"  - Bucket: {bucket_name}")
    print(f"  - Auth: Uses AWS environment credentials")
    print(f"\n✓ Block saved to Prefect Cloud/Server!")
    print(f"\nThe flow is already configured to use 's3-bucket/{block_name}' for result storage.")
    print(f"No additional configuration needed!")


if __name__ == "__main__":
    main()
