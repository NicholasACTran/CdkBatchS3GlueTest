from aws_cdk import (
                     aws_sqs as sqs,
                     aws_s3 as s3,
                     aws_s3_notifications as s3_notifications,
                     aws_iam as iam,
                     aws_glue as glue,
                     aws_lakeformation as lakeformation,
                     aws_events as events,
                     Aws, CfnOutput
                     )
from constructs import Construct

class GlueWorkflow(Construct):
    def __init__(self, scope: Construct, id: str, s3_bucket, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        glue_queue = sqs.Queue(self, 'test_glue_queue')
        s3_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, s3_notifications.SqsDestination(glue_queue))

        
        glue_role = iam.Role(
            self,
            'glue_role',
            role_name='GlueRole',
            description='Role for Glue services to access S3',
            assumed_by=iam.ServicePrincipal('glue.amazonaws.com'),
            inline_policies={
                'glue_policy': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                's3:*', 
                                'glue:*', 
                                'iam:*', 
                                'logs:*',
                                'cloudwatch:*', 
                                'sqs:*', 
                                'ec2:*',
                                'cloudtrail:*'
                                ],
                            resources=['*']
                            )])})
        
        glue_database = glue.CfnDatabase(
            self, 
            'glue-database',
            catalog_id=Aws.ACCOUNT_ID,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name='mondaycom-database',
                description='Database to store mondaycom raw data.'))
        
        lakeformation.CfnPermissions(
            self,
            'lakeformation_permission',
            data_lake_principal=lakeformation.CfnPermissions.DataLakePrincipalProperty(
                data_lake_principal_identifier=glue_role.role_arn
                ),
            resource=lakeformation.CfnPermissions.ResourceProperty(
                database_resource=lakeformation.CfnPermissions.DatabaseResourceProperty(
                    catalog_id=glue_database.catalog_id,
                    name='mondaycom-database'
                    )
                ),
            permissions=['ALL']
            )
        
        
        glue_crawler = glue.CfnCrawler(
            self,
            'glue_crawler',
            name='glue_crawler',
            role=glue_role.role_arn,
            database_name='mondaycom-database',
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    glue.CfnCrawler.S3TargetProperty(
                        path=f's3://{s3_bucket.bucket_name}/',
                        event_queue_arn=glue_queue.queue_arn)
                    ]
                ),
            recrawl_policy=glue.CfnCrawler.RecrawlPolicyProperty(
                recrawl_behavior='CRAWL_EVENT_MODE'
                )
            )
        
        glue_crawler.add_dependency(glue_database)
        
        glue_workflow = glue.CfnWorkflow(
            self, 
            'glue_workflow',
            name='glue_workflow',
            description='Workflow to process the mondays.com data.'
            )
        
        glue_trigger = glue.CfnTrigger(
            self,
            'glue_crawler_trigger',
            name='glue_crawler_trigger',
            actions=[
                glue.CfnTrigger.ActionProperty(
                    crawler_name=glue_crawler.name,
                    notification_property=glue.CfnTrigger.NotificationPropertyProperty(notify_delay_after=3),
                    timeout=3
                    )
                ],
            type='EVENT',
            workflow_name=glue_workflow.name
        )

        glue_trigger.add_dependency(glue_workflow)
        glue_trigger.add_dependency(glue_crawler)

        rule_role = iam.Role(
            self,
            'rule_role',
            role_name='EventBridgeRole',
            description='Role for EventBridge to trigger Glue workflows.',
            assumed_by=iam.ServicePrincipal('events.amazonaws.com'),
            inline_policies={
                'eventbridge_policy': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                'events:*',
                                'glue:*'
                                ],
                            resources=['*']
                            )])})

        events.CfnRule(
            self, 
            'rule_s3_glue',
            name='rule_s3_glue',
            role_arn=rule_role.role_arn,
            targets=[
                events.CfnRule.TargetProperty(
                    arn=f'arn:aws:glue:{Aws.REGION}:{Aws.ACCOUNT_ID}:workflow/{glue_workflow.name}',
                    role_arn=rule_role.role_arn,
                    id=Aws.ACCOUNT_ID
                    )
                ],
            event_pattern={
                "detail-type": ["Object Created"],
                "detail": {
                    "bucket": {
                        "name": [f"{s3_bucket.bucket_name}"]
                        }
                    },
                "source": ["aws.s3"]})

        pass

    def __output__(self):
        CfnOutput(self, 'Pipeline ARN', value=self.pipeline.pipeline_arn)