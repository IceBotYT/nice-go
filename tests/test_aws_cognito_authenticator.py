from unittest.mock import patch

from nice_go._aws_cognito_authenticator import AwsCognitoAuthenticator


async def test_refresh_token(mock_authenticator: AwsCognitoAuthenticator) -> None:
    with patch("nice_go._aws_cognito_authenticator.boto3.client") as mock_boto3_client:
        mock_boto3_client.return_value.initiate_auth.return_value = {
            "AuthenticationResult": {"IdToken": "test_token"},
        }
        result = mock_authenticator.refresh_token("refresh_token")

        assert result.id_token == "test_token"


async def test_get_new_token(mock_authenticator: AwsCognitoAuthenticator) -> None:
    with patch(
        "nice_go._aws_cognito_authenticator.boto3.client",
    ) as mock_boto3_client, patch(
        "nice_go._aws_cognito_authenticator.AWSSRP",
    ) as mock_awssrp:
        mock_boto3_client.return_value.initiate_auth.return_value = {
            "ChallengeParameters": {"key": "value"},
        }
        mock_boto3_client.return_value.respond_to_auth_challenge.return_value = {
            "AuthenticationResult": {"IdToken": "test_token"},
        }
        mock_awssrp.return_value.get_auth_params.return_value = {"key": "value"}
        mock_awssrp.return_value.process_challenge.return_value = {"key": "value"}
        result = mock_authenticator.get_new_token("username", "password")

        assert result.id_token == "test_token"
        assert result.refresh_token is None
