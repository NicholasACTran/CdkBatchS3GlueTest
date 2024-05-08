from aws_cdk import (
                     aws_ecr as ecr,
                     aws_iam as iam,
                     aws_s3 as s3,
                     aws_sns as sns,
                     aws_lambda as _lambda,
                     aws_events as events,
                     aws_events_targets as event_targets,
                     App, Stack, RemovalPolicy
                     )
from constructs import Construct

from cdk_batch_s3_glue_test.pipeline import Pipeline
from cdk_batch_s3_glue_test.batch_with_fargate import BatchWithFargate
from cdk_batch_s3_glue_test.glue_workflow import GlueWorkflow

from utils.constants import (
    ECR_REPO_NAME,
    S3_BUCKET_NAME,
    SNS_TOPIC,
    LAMBDA_NAME,
    LAMBDA_IAM_ROLE
)

class CdkBatchS3GlueTestStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ecrRepo = ecr.Repository(self, ECR_REPO_NAME)
        bucket = s3.Bucket(
            self,
            'CDKBatchS3GlueTestBucket',
            bucket_name=S3_BUCKET_NAME,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            event_bridge_enabled=True,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        sns_topic = sns.Topic(self, SNS_TOPIC)
        lambda_role = iam.Role(
            self,
            LAMBDA_IAM_ROLE,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSNSFullAccess")
            ]
        )
        __lambda = _lambda.Function(
            self, LAMBDA_NAME,
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset('lambda'),
            handler='schema_change.lambda_handler',
            environment={
                'SNS_TOPIC': SNS_TOPIC
            },
            role=lambda_role
        )

        # __lambda.add_to_role_policy(lambda_role)
        event_pattern = events.EventPattern(
            source=['aws.glue'],
            detail_type=['Glue Crawler State Change'],
            detail={
                'state':['Succeeded']
            }
        )
        lambda_trigger_rule = events.Rule(
            self, "Glue schema change event Rule",
            description="Trigger Lambda on successful crawl",
            event_pattern=event_pattern,
            targets=[]
            )
        lambda_trigger_rule.add_target(
            event_targets.LambdaFunction(__lambda)
        )

        pipeline = Pipeline(
            self,
            id='TestPipeline',
            ecrRepo=ecrRepo
        )

        batch = BatchWithFargate(
            self, 
            id="TestJob", 
            ecrRepo=ecrRepo
        )

        glue_workflow = GlueWorkflow(
            self,
            id="TestWorkflow",
            s3_bucket=bucket
        )

app = App()
CdkBatchS3GlueTestStack(app, "CdkBatchS3GlueTestStack")
app.synth()