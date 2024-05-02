from datetime import datetime
import io
import json
import requests

import boto3
import pandas as pd

def get_first_items_page(apiUrl, headers, board_id):

    query_item = f"""
    query {{
        boards (ids: [{board_id}]){{
            items_page (limit:500){{
                cursor
                    items {{
                        id 
                        created_at 
                        name 
                        board {{
                            id
                        }}
                    column_values {{
                        id,
                        text, 
                        type, 
                        value
                    }}
                }}
            }}
        }}
    }}
    """

    data = {"query": query_item}
    r = requests.post(url=apiUrl, json=data, headers=headers)
    print(r.json())
    return r.json()

def write_parquet_to_s3(file_name_str, df, dest_s3path_str):
    
    new_file_name = f"{file_name_str}.parquet"
    bucket_name = dest_s3path_str.split("/")[2]
    path_after_bucket = dest_s3path_str.replace("s3://", "")
    index = path_after_bucket.find("/")
    file_path = path_after_bucket[index + 1 :]
    try:
        # Convert DataFrame to Parquet bytes
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer, index=False)

        # Write Parquet data to S3
        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_path + new_file_name,
            Body=parquet_buffer.getvalue(),
        )

        print(f"Parquet files written to {dest_s3path_str}")
        return None
    except Exception as e:
        print(f"Error writing files to {dest_s3path_str}: {e}")
        return None
    
if __name__ == '__main__':
    
    ds = datetime.now().strftime("%Y-%m-%d")
    dt = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    warehouse_s3path_dest = f"s3://cdk-batch-s3-glue-test-bucket/monday.com/items/{ds}/"

    secrets_client = boto3.client('secretsmanager')
    secret = secrets_client.get_secret_value(SecretId='/api_keys/MONDAYS_COM')
    API_KEY = json.loads(secret)['/api_keys/MONDAYS_COM']

    api_url = "https://api.monday.com/v2"
    headers = {"Authorization": API_KEY}

    board_ids = ["6255740472", "6058656936", "6125794481"]
    # ids for  [monday_listings board, monday_dispositions PGY, monday_dispositions SLD]

    for board_id in board_ids:
        print(f"Processing board: {board_id}...")
        response = get_first_items_page(api_url, headers, board_id)
        data = (
            response.get("data", None)
            .get("boards", None)[0]
            .get("items_page", None)
            .get("items", None)
        )

        if board_id == board_ids[0]:
            df = pd.json_normalize(data)
        else:
            tmp_df = pd.json_normalize(data)
            df = pd.concat([df, tmp_df])

    df.rename(columns={"board.id": "board_id"}, inplace=True)
    df['loaded_at'] = datetime.now()
    df['loaded_at'] = df['loaded_at'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f"The table shape: {df.shape}")

    write_parquet_to_s3(dt, df, warehouse_s3path_dest)

    print(f"Processing complete.")
