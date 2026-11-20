import json
import math
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = os.getenv("TABLE_NAME", "retail_supply_chain_snapshots")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)


def _convert_decimals(obj):
    if isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _convert_decimals(value) for key, value in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def _get_latest_sku_snapshot(store_id: str, product_id: str):
    response = table.query(
        KeyConditionExpression=Key("store_product_key").eq(f"{store_id}#{product_id}"),
        ScanIndexForward=False,
        Limit=1,
    )
    items = response.get("Items", [])
    return _convert_decimals(items[0]) if items else {"error": "No snapshot found"}


def _get_sku_history(store_id: str, product_id: str, start_date: str, end_date: str):
    response = table.query(
        KeyConditionExpression=(
            Key("store_product_key").eq(f"{store_id}#{product_id}")
            & Key("snapshot_date").between(start_date, end_date)
        )
    )
    return _convert_decimals(response.get("Items", []))


def _list_region_day_snapshots(region: str, snapshot_date: str, limit: int = 5):
    response = table.query(
        IndexName="region_date_index",
        KeyConditionExpression=Key("region_date_key").eq(f"{region}#{snapshot_date}"),
        Limit=int(limit or 5),
    )
    return _convert_decimals(response.get("Items", []))


def _simulate_reorder_recommendation(store_id: str, product_id: str, cover_days: int, lead_time_days: int):
    snapshot = _get_latest_sku_snapshot(store_id, product_id)
    if "error" in snapshot:
        return snapshot

    inventory = float(snapshot.get("current_inventory", 0))
    daily_demand = float(snapshot.get("estimated_daily_demand", 0))
    projected_stock_at_arrival = round(inventory - (daily_demand * lead_time_days), 2)
    target_stock = daily_demand * (cover_days + lead_time_days)
    draft_order_qty = max(0, int(math.ceil(target_stock - inventory)))

    return {
        "store_id": store_id,
        "product_id": product_id,
        "snapshot_date": snapshot.get("snapshot_date"),
        "current_inventory": inventory,
        "estimated_daily_demand": daily_demand,
        "lead_time_days": lead_time_days,
        "cover_days": cover_days,
        "projected_stock_at_arrival": projected_stock_at_arrival,
        "draft_recommended_order_qty": draft_order_qty,
        "requires_human_approval": True,
    }


def lambda_handler(event, context):
    custom_context = getattr(getattr(context, "client_context", None), "custom", {}) or {}
    tool_name = event.get("tool_name") or custom_context.get("bedrockAgentCoreToolName") or ""
    normalized_tool = tool_name.split("___")[-1]
    arguments = event.get("arguments", event)

    if normalized_tool == "get_latest_sku_snapshot":
        result = _get_latest_sku_snapshot(arguments["store_id"], arguments["product_id"])
    elif normalized_tool == "get_sku_history":
        result = _get_sku_history(arguments["store_id"], arguments["product_id"], arguments["start_date"], arguments["end_date"])
    elif normalized_tool == "list_region_day_snapshots":
        result = _list_region_day_snapshots(arguments["region"], arguments["snapshot_date"], arguments.get("limit", 5))
    elif normalized_tool == "simulate_reorder_recommendation":
        result = _simulate_reorder_recommendation(arguments["store_id"], arguments["product_id"], int(arguments["cover_days"]), int(arguments["lead_time_days"]))
    else:
        return {"statusCode": 400, "body": json.dumps({"error": f"Unknown tool: {tool_name}"})}

    return {"statusCode": 200, "body": json.dumps(result)}
