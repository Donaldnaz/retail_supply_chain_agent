#!/usr/bin/env bash
set -euo pipefail

export AWS_REGION="us-east-1"
TABLE_NAME="retail_supply_chain_snapshots"

aws dynamodb create-table \
  --region "$AWS_REGION" \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=store_product_key,AttributeType=S \
    AttributeName=snapshot_date,AttributeType=S \
    AttributeName=region_date_key,AttributeType=S \
  --key-schema \
    AttributeName=store_product_key,KeyType=HASH \
    AttributeName=snapshot_date,KeyType=RANGE \
  --global-secondary-indexes \
    "IndexName=region_date_index,KeySchema=[{AttributeName=region_date_key,KeyType=HASH},{AttributeName=snapshot_date,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=0,WriteCapacityUnits=0}" \
  --billing-mode PAY_PER_REQUEST

aws dynamodb wait table-exists --region "$AWS_REGION" --table-name "$TABLE_NAME"
aws dynamodb put-item --region "$AWS_REGION" --table-name "$TABLE_NAME" --item file://infra/sample-snapshot-s001-p0001.json

aws dynamodb get-item \
  --region "$AWS_REGION" \
  --table-name "$TABLE_NAME" \
  --key '{"store_product_key":{"S":"S001#P0001"},"snapshot_date":{"S":"2024-01-01"}}'
