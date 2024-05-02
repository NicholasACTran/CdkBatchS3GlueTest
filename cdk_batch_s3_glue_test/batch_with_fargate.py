from aws_cdk import (
                     aws_ec2 as ec2, 
                     aws_batch as batch,
                     aws_ecs as ecs,
                     aws_iam as iam,
                     CfnOutput, Size
                     )
from constructs import Construct

class BatchWithFargate(Construct):
    def __init__(self, scope: Construct, id: str, ecrRepo, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create AWS Batch Job Queue
        self.batch_queue = batch.JobQueue(self, "JobQueue")

        self.__create_batch_compute_environments__(3)

        # Task execution IAM role for Fargate
        task_execution_role = iam.Role(self, "TaskExecutionRole",
                                  assumed_by=iam.ServicePrincipal(
                                      "ecs-tasks.amazonaws.com"),
                                  managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")])

        # Create Job Definition to submit job in batch job queue.
        self.batch_jobDef = batch.EcsJobDefinition(self, "MyJobDef",
                                           container=batch.EcsFargateContainerDefinition(self, "FargateCDKJobDef",
                                               image=ecs.ContainerImage.from_ecr_repository(ecrRepo),
                                               command=["python", "test.py"],
                                               memory=Size.mebibytes(512),
                                               cpu=0.25,
                                               execution_role=task_execution_role
                                           )
        )

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

    def __output__(self):
        CfnOutput(self, "BatchJobQueue",value=self.batch_queue.job_queue_name)
        CfnOutput(self, "JobDefinition",value=self.batch_jobDef.job_definition_name)