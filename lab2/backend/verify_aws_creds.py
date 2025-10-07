#!/usr/bin/env python3
"""Verify AWS credentials are available for MCP subprocess"""
import os
import sys
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

print("🔍 Checking AWS Credentials for MCP...")
print()

# Check environment variables
has_access_key = bool(os.environ.get('AWS_ACCESS_KEY_ID'))
has_secret_key = bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))
has_region = bool(os.environ.get('AWS_DEFAULT_REGION') or os.environ.get('AWS_REGION'))

if has_access_key:
    print(f"✅ AWS_ACCESS_KEY_ID: {os.environ['AWS_ACCESS_KEY_ID'][:10]}...")
else:
    print("⚠️  AWS_ACCESS_KEY_ID: Not in environment (checking IAM role...)")

if has_secret_key:
    print(f"✅ AWS_SECRET_ACCESS_KEY: {os.environ['AWS_SECRET_ACCESS_KEY'][:10]}...")
else:
    print("⚠️  AWS_SECRET_ACCESS_KEY: Not in environment (checking IAM role...)")

region = os.environ.get('AWS_DEFAULT_REGION') or os.environ.get('AWS_REGION') or 'us-west-2'
print(f"✅ AWS_REGION: {region}")

if os.environ.get('AWS_SESSION_TOKEN'):
    print(f"✅ AWS_SESSION_TOKEN: {os.environ['AWS_SESSION_TOKEN'][:10]}...")

print()
print("🔍 Testing boto3 credentials (includes IAM role check)...")

try:
    # Try to get caller identity - works with IAM role or access keys
    sts = boto3.client('sts', region_name=region)
    identity = sts.get_caller_identity()
    
    print("✅ AWS credentials are valid!")
    print(f"   Account: {identity['Account']}")
    print(f"   User/Role: {identity['Arn'].split('/')[-1]}")
    print(f"   Method: {'IAM Role' if 'assumed-role' in identity['Arn'] else 'Access Keys'}")
    print()
    print("✅ MCP subprocess will be able to access AWS services")
    sys.exit(0)
    
except NoCredentialsError:
    print("❌ No AWS credentials found!")
    print()
    print("EC2 Instance: Check IAM role is attached")
    print("Local Dev: Run one of these:")
    print("  export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)")
    print("  export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)")
    print("  export AWS_SESSION_TOKEN=$(aws configure get aws_session_token)")
    sys.exit(1)
    
except ClientError as e:
    print(f"❌ AWS credentials invalid: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Error checking credentials: {e}")
    sys.exit(1)
