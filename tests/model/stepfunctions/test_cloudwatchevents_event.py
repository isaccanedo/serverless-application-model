from unittest import TestCase
from unittest.mock import Mock

from samtranslator.model.exceptions import InvalidEventException
from samtranslator.model.stepfunctions.events import CloudWatchEvent


class CloudWatchEventsEventSource(TestCase):
    def setUp(self):
        self.logical_id = "CWEEvent"

        self.cwe_event_source = CloudWatchEvent(self.logical_id)
        self.cwe_event_source.Pattern = {"detail": {"state": ["terminated"]}}

        self.state_machine = Mock()
        self.state_machine.get_runtime_attr = Mock()
        self.state_machine.get_runtime_attr.return_value = "arn:aws:statemachine:mock"
        self.state_machine.resource_attributes = {}
        self.state_machine.get_passthrough_resource_attributes = Mock()
        self.state_machine.get_passthrough_resource_attributes.return_value = {}

    def test_to_cloudformation_returns_eventrule_and_role_resources(self):
        resources = self.cwe_event_source.to_cloudformation(resource=self.state_machine)
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].resource_type, "AWS::Events::Rule")
        self.assertEqual(resources[1].resource_type, "AWS::IAM::Role")

        iam_role = resources[1]
        self.assertEqual(
            iam_role.AssumeRolePolicyDocument,
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": ["sts:AssumeRole"],
                        "Effect": "Allow",
                        "Principal": {"Service": ["events.amazonaws.com"]},
                    }
                ],
            },
        )
        self.assertEqual(
            iam_role.Policies,
            [
                {
                    "PolicyName": "CWEEventRoleStartExecutionPolicy",
                    "PolicyDocument": {
                        "Statement": [
                            {
                                "Action": "states:StartExecution",
                                "Resource": "arn:aws:statemachine:mock",
                                "Effect": "Allow",
                            }
                        ]
                    },
                }
            ],
        )

        event_rule = resources[0]
        self.assertEqual(event_rule.EventPattern, {"detail": {"state": ["terminated"]}})
        self.assertEqual(
            event_rule.Targets,
            [
                {
                    "Id": "CWEEventStepFunctionsTarget",
                    "Arn": "arn:aws:statemachine:mock",
                    "RoleArn": {"Fn::GetAtt": [iam_role.logical_id, "Arn"]},
                }
            ],
        )

    def test_to_cloudformation_throws_when_no_resource(self):
        self.assertRaises(TypeError, self.cwe_event_source.to_cloudformation)

    def test_to_cloudformation_with_input(self):
        input_to_service = '{"test_key": "test_value"}'
        self.cwe_event_source.Input = input_to_service
        resources = self.cwe_event_source.to_cloudformation(resource=self.state_machine)
        self.assertEqual(len(resources), 2)
        event_rule = resources[0]
        self.assertEqual(event_rule.Targets[0]["Input"], input_to_service)

    def test_to_cloudformation_with_input_path(self):
        input_path_to_service = "path/to/input"
        self.cwe_event_source.InputPath = input_path_to_service
        resources = self.cwe_event_source.to_cloudformation(resource=self.state_machine)
        self.assertEqual(len(resources), 2)
        event_rule = resources[0]
        self.assertEqual(event_rule.Targets[0]["InputPath"], input_path_to_service)

    def test_to_cloudformation_with_eventbus_name(self):
        input_to_service = '{"test_key": "test_value"}'
        self.cwe_event_source.Input = input_to_service
        resources = self.cwe_event_source.to_cloudformation(resource=self.state_machine)
        self.assertEqual(len(resources), 2)
        event_rule = resources[0]
        self.assertEqual(event_rule.Targets[0]["Input"], input_to_service)

    def test_to_cloudformation_with_retry_policy(self):
        retry_policy = {"MaximumRetryAttempts": "10", "MaximumEventAgeInSeconds": "300"}
        self.cwe_event_source.RetryPolicy = retry_policy
        resources = self.cwe_event_source.to_cloudformation(resource=self.state_machine)
        self.assertEqual(len(resources), 2)
        event_rule = resources[0]
        self.assertEqual(event_rule.Targets[0]["RetryPolicy"], retry_policy)

    def test_to_cloudformation_with_dlq_arn_provided(self):
        dead_letter_config = {"Arn": "DeadLetterQueueArn"}
        self.cwe_event_source.DeadLetterConfig = dead_letter_config
        resources = self.cwe_event_source.to_cloudformation(resource=self.state_machine)
        self.assertEqual(len(resources), 2)
        event_rule = resources[0]
        self.assertEqual(event_rule.Targets[0]["DeadLetterConfig"], dead_letter_config)

    def test_to_cloudformation_invalid_both_dlq_arn_and_type_provided(self):
        dead_letter_config = {"Arn": "DeadLetterQueueArn", "Type": "SQS"}
        self.cwe_event_source.DeadLetterConfig = dead_letter_config
        with self.assertRaises(InvalidEventException):
            self.cwe_event_source.to_cloudformation(resource=self.state_machine)

    def test_to_cloudformation_invalid_dlq_type_provided(self):
        dead_letter_config = {"Type": "SNS", "QueueLogicalId": "MyDLQ"}
        self.cwe_event_source.DeadLetterConfig = dead_letter_config
        with self.assertRaises(InvalidEventException):
            self.cwe_event_source.to_cloudformation(resource=self.state_machine)

    def test_to_cloudformation_missing_dlq_type_or_arn(self):
        dead_letter_config = {"QueueLogicalId": "MyDLQ"}
        self.cwe_event_source.DeadLetterConfig = dead_letter_config
        with self.assertRaises(InvalidEventException):
            self.cwe_event_source.to_cloudformation(resource=self.state_machine)

    def test_to_cloudformation_with_dlq_generated(self):
        dead_letter_config = {"Type": "SQS"}
        dead_letter_config_translated = {"Arn": {"Fn::GetAtt": [self.logical_id + "Queue", "Arn"]}}
        self.cwe_event_source.DeadLetterConfig = dead_letter_config
        resources = self.cwe_event_source.to_cloudformation(resource=self.state_machine)
        self.assertEqual(len(resources), 4)
        event_rule = resources[0]
        self.assertEqual(event_rule.Targets[0]["DeadLetterConfig"], dead_letter_config_translated)

    def test_to_cloudformation_with_dlq_generated_with_custom_logical_id(self):
        dead_letter_config = {"Type": "SQS", "QueueLogicalId": "MyDLQ"}
        dead_letter_config_translated = {"Arn": {"Fn::GetAtt": ["MyDLQ", "Arn"]}}
        self.cwe_event_source.DeadLetterConfig = dead_letter_config
        resources = self.cwe_event_source.to_cloudformation(resource=self.state_machine)
        self.assertEqual(len(resources), 4)
        event_rule = resources[0]
        self.assertEqual(event_rule.Targets[0]["DeadLetterConfig"], dead_letter_config_translated)
