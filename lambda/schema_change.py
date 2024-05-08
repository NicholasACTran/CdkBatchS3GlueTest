
import json
import boto3
import logging
import os

SNS_TOPIC = os.environ['SNS_TOPIC']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

glue = boto3.client('glue')
sns = boto3.client('sns')


def lambda_handler(event, context):
    
    logger.info(event)
    
    crawler_name=get_crawler_name(event)
    crawl_id=get_crawl_id(crawler_name)
    database=get_database(crawler_name)
    
    try:
        tables_deleted, tables_updated_or_deprecated, tables_added=get_crawler_report(crawler_name, crawl_id)
        compare_version_report, tables_deprecated=get_compare_version_report(database,tables_updated_or_deprecated, tables_deleted)
        send_compare_version_report(compare_version_report, tables_deleted, tables_added, tables_deprecated,crawler_name, crawl_id, database )
        
    except NoChangeError as error:
        logger.warn("No change has been detected")
    
    
def get_crawler_name(event):
    return event['detail']['crawlerName']

def get_crawl_id(crawler_name):
    return glue.list_crawls(CrawlerName=crawler_name)['Crawls'][0]['CrawlId']

def get_database(crawler_name):
    return glue.get_crawler(Name=crawler_name)['Crawler']['DatabaseName']
    
def get_crawler_report(crawler_name, crawl_id):
    crawl= _get_crawl_by_crawl_id(crawler_name, crawl_id )
    
    try :
        raw_report=json.loads(crawl['Summary'])
    
    except KeyError as error:
        raise NoChangeError
    
    if raw_report['TABLE'].get('DELETE'):
        tables_deleted=json.loads(raw_report['TABLE']['DELETE'])['Details']['names']
    else:
        tables_deleted=[]
    
    if raw_report['TABLE'].get('UPDATE'):
        tables_updated_or_deprecated=json.loads(raw_report['TABLE']['UPDATE'])['Details']['names']
    else:
        tables_updated=[]
    
    if raw_report['TABLE'].get('ADD'):
        tables_added=json.loads(raw_report['TABLE']['ADD'])['Details']['names']
    else:
        tables_added=[]
    
    return tables_deleted, tables_updated_or_deprecated, tables_added
        
       
def get_compare_version_report(database,tables_updated_or_deprecated, tables_deleted):
    
    comparare_version_report=[]
    table_deprecated=[]
    
    for table in tables_updated_or_deprecated:
        versions=glue.get_table_versions(DatabaseName=database, TableName=table)
        try:
            if versions['TableVersions'][0]['Table']['Parameters']['DEPRECATED_BY_CRAWLER']:
                table_deprecated.append(table)
        
        except KeyError:
    
            new_table= versions['TableVersions'][0]['Table']['StorageDescriptor']['Columns']
            old_table= versions['TableVersions'][1]['Table']['StorageDescriptor']['Columns']
    
            dropped_columns=_find_dropped_columns(old_table, new_table)
            added_columns=_find_added_columns(old_table, new_table)
            updated_columns=_find_updated_columns(old_table, new_table, table)
            
            comparare_version_report.append({'table_name':table, 'dropped_columns':dropped_columns, 'added_columns':added_columns, 'updated_columns':updated_columns})
        
    return comparare_version_report, table_deprecated
        
        
def _find_dropped_columns(old_table, new_table):
    new_table_columun_names= set(column['Name'] for column in new_table)
    old_table_columun_names= set(column['Name'] for column in old_table)
    return old_table_columun_names-new_table_columun_names
    

def _find_added_columns(old_table, new_table):
    new_table_columun_names= set(column['Name'] for column in new_table)
    old_table_columun_names= set(column['Name'] for column in old_table)
    return new_table_columun_names-old_table_columun_names

def _find_updated_columns(old_table, new_table, table):
    updated_columns=[]
    for old_column in old_table:
        for new_column in new_table:
            if (old_column["Name"]==new_column["Name"]) and (old_column["Type"]!=new_column["Type"]):
                updated_columns.append({'column_name': old_column["Name"] , 'old_type':old_column["Type"], 'new_type':new_column["Type"]})
    return updated_columns

def _get_crawl_by_crawl_id(crawler_name, crawl_id ):
    crawl=glue.list_crawls(CrawlerName=crawler_name, MaxResults=1,
    Filters=[
        {
            'FieldName': 'CRAWL_ID',
            'FilterOperator': 'EQ',
            'FieldValue': crawl_id
       }])['Crawls'][0]
    if crawl is not None:
        return crawl
    else:
        raise NoCrawlFoundError()

def send_compare_version_report(compare_version_report, tables_deleted, tables_added, tables_deprecated,crawler_name, crawl_id, database ):
    nl="\n"
    message=f"""Dear Operator,
The Crawler '{crawler_name}' updated the database {database} (crawl id :{crawl_id})
The following tables are deleted from the database:
{nl.join(tables_deleted)}
The following tables are deprecated from the database:
{nl.join(tables_deprecated)}
The following tables are added to the database:
{nl.join(tables_added)}
The following tables are updated:
{nl.join([str(column_report) for column_report in compare_version_report])}"""

    sns.publish(TopicArn=SNS_TOPIC, Message=message, Subject=f"Crawler {crawler_name} detects schema changes")


    
class NoChangeError(Exception):
    """ Exception thrown when no change is detected"""
    pass

class NoCrawlFoundError(Exception):
    """ Exception thrown when no specific crawl is found"""
    pass
                