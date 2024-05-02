from aws_cdk import (
                     aws_ec2 as ec2, 
                     aws_batch as batch,
                     aws_ecs as ecs,
                     aws_iam as iam,
                     aws_events as events,
                     aws_events_targets as events_targets,
                     CfnOutput, Size
                     )
from constructs import Construct

class BatchWithFargate(Construct):
    def __init__(self, scope: Construct, id: str, ecrRepo, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create AWS Batch Job Queue
        self.batch_queue = batch.JobQueue(self, "JobQueue")

        self.__create_batch_compute_environments__(3)

        # Create Job Definition to submit job in batch job queue.
        self.batch_jobDef = self.__create_batch_job_definition_(ecrRepo)

        self.__create_batch_job_on_push__(ecrRepo)

        self.__output__()

    def __create_batch_compute_environments__(self, count: int):

        # This resource alone will create a private/public subnet in each AZ as well as nat/internet gateway(s)
        vpc = ec2.Vpc(self, "VPC")

        # For loop to create Batch Compute Environments
        for i in range(count):
            name = "MyFargateEnv" + str(i)
            fargate_spot_environment = batch.FargateComputeEnvironment(self, name,
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                vpc=vpc
            )

            self.batch_queue.add_compute_environment(fargate_spot_environment, i)
    
    def __create_batch_job_definition_(self, ecrRepo) -> batch.EcsJobDefinition:
        
        # Task execution IAM role for Fargate
        task_execution_role = iam.Role(
            self, 
            "TaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
                ]
        )
        
        return batch.EcsJobDefinition(
            self, 
            "MyJobDef",
            container=batch.EcsFargateContainerDefinition(
                self,
                "FargateCDKJobDef",
                image=ecs.ContainerImage.from_ecr_repository(ecrRepo),
                command=["python", "test.py"],
                memory=Size.mebibytes(512),
                cpu=0.25,
                execution_role=task_execution_role
            )
        )
    
    def __create_batch_job_on_push__(self, ecrRepo):
        event_pattern = events.EventPattern(
            detail_type=['ECR Image Action'],
            detail={
                "result": ["SUCCESS"],
                "action-type": ["PUSH"],
                "image-tag": ["latest"],
                "repository-name": [ecrRepo.repository_name]
            }
        )

        ecr_batch_trigger_rule = events.Rule(
            self, "ECR to Batch Rule",
            description="Trigger a Batch job on push to ECR",
            event_pattern=event_pattern,
            targets=[events_targets.BatchJob(
                job_queue_arn=self.batch_queue.job_queue_arn,
                job_queue_scope=self.batch_queue,
                job_definition_arn=self.batch_jobDef.job_definition_arn,
                job_definition_scope=self.batch_jobDef
            )])

    def __output__(self):
        CfnOutput(self, "BatchJobQueue",value=self.batch_queue.job_queue_name)
        CfnOutput(self, "JobDefinition",value=self.batch_jobDef.job_definition_name)