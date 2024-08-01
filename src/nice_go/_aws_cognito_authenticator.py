"""AWS Cognito authentication and identity management.

This module provides a class to handle AWS Cognito authentication and identity
management.

Info:
    You do not need to use this module directly. It is used by the `nice_go_api`
    module to authenticate with AWS Cognito.
"""

import logging

import boto3
from aiobotocore.session import get_session
from pycognito import AWSSRP  # type: ignore[import-untyped]

from nice_go._authentication_tokens import AuthenticationTokens

_LOGGER = logging.getLogger(__name__)


class AwsCognitoAuthenticator:
    """Handles AWS Cognito authentication and identity management.

    This class provides methods to authenticate with AWS Cognito and retrieve
    authentication tokens. It can be used to refresh tokens or to get new tokens
    by providing a username and password.

    Args:
        region_name (str): The AWS region name.
        client_id (str): The AWS Cognito client ID.
        pool_id (str): The AWS Cognito pool ID.
        identity_pool_id (str): The AWS Cognito identity pool ID.

    Attributes:
        region_name (str): The AWS region name.
        identity_pool_id (str): The AWS Cognito identity pool ID.
        client_id (str): The AWS Cognito client ID.
        pool_id (str): The AWS Cognito pool ID.
        session (botocore.session.Session): The botocore session object.
    """

    def __init__(
        self,
        region_name: str,
        client_id: str,
        pool_id: str,
        identity_pool_id: str,
    ) -> None:
        """Initialize the AwsCognitoAuthenticator object."""
        self.region_name = region_name
        self.identity_pool_id = identity_pool_id
        self.client_id = client_id
        self.pool_id = pool_id
        self.session = get_session()

    def refresh_token(self, refresh_token: str) -> AuthenticationTokens:
        """Regenerates the token by providing a refresh token.

        Args:
            refresh_token (str): The refresh token.

        Returns:
            The new authentication tokens.
        """
        _LOGGER.debug("Refreshing token")
        cognito_identity_provider = boto3.client("cognito-idp", self.region_name)
        resp = cognito_identity_provider.initiate_auth(
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={
                "REFRESH_TOKEN": refresh_token,
            },
            ClientId=self.client_id,
        )
        _LOGGER.debug("Token refreshed")
        return AuthenticationTokens(resp["AuthenticationResult"])

    def get_new_token(self, username: str, password: str) -> AuthenticationTokens:
        """Gets the initial token by providing username and password.

        Args:
            username (str): The username.
            password (str): The password.

        Returns:
            The new authentication tokens.
        """
        _LOGGER.debug("Getting new token")
        cognito_identity_provider = boto3.client("cognito-idp", self.region_name)
        # Start the authentication flow
        aws_srp = AWSSRP(
            username=username,
            password=password,
            pool_id=self.pool_id,
            client_id=self.client_id,
            client=cognito_identity_provider,
        )

        _LOGGER.debug("Initiating auth")

        auth_params = aws_srp.get_auth_params()
        resp = cognito_identity_provider.initiate_auth(
            AuthFlow="USER_SRP_AUTH",
            AuthParameters=auth_params,
            ClientId=self.client_id,
        )

        _LOGGER.debug("Auth initiated, responding to challenge")

        challenge_response = aws_srp.process_challenge(
            resp["ChallengeParameters"],
            auth_params,
        )

        # Respond to PASSWORD_VERIFIER
        resp = cognito_identity_provider.respond_to_auth_challenge(
            ClientId=self.client_id,
            ChallengeName="PASSWORD_VERIFIER",
            ChallengeResponses=challenge_response,
        )

        _LOGGER.debug("Token received")

        return AuthenticationTokens(resp["AuthenticationResult"])
