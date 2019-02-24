import json
from unittest.mock import patch, Mock

from django.urls import reverse
from requests import Response

from meals.tests.test_base import BaseTestCase
from meals.views.admin import logger as admin_logger


class OAuthLandingTest(BaseTestCase):
    def test_oauth_error(self):
        """Tests when user did not authorize the HypoMeals app, or other errors"""
        data = {
            "error": "User declined permission request.",
            "error_description": "Blah",
        }
        with self.assertLogs(logger=admin_logger, level="WARNING"):
            resp = self.client.get(reverse("sso_landing"), data=data)

        self.assertRedirects(resp, expected_url=reverse("login"))

    def test_no_token(self):
        """Tests when no auth token was returned by OAuth API"""
        data = {"fragment": ""}
        resp = self.ajax_post(reverse("sso_landing"), data=data)
        self.assertJSONEqual(resp.content, {"error": None, "resp": reverse("error")})
        resp = self.client.get(reverse("error"))
        # When the user is eventually redirected, he/she should get this error message.
        self.assertContains(
            resp,
            status_code=200,
            text="Single sign-on did not return valid access token",
        )

    @patch("meals.views.admin.requests")
    @patch("meals.views.admin.settings")
    @patch("meals.views.admin.sign_in_netid_user")
    def test_identity_api(self, mock_sign_in, mock_settings, mock_requests):
        """Tests when IDENTITY_API returns correct response"""
        mock_settings.OAUTH_CLIENT_ID = "123"
        mock_settings.IDENTITY_API_URL = "https://fake.oit.duke.edu"
        mock_response = Mock(spec=Response)
        mock_requests.get.return_value = mock_response
        mock_response.status_code = 200

        identity_resp = {"netid": "abc123", "firstName": "Test", "lastName": "User"}
        mock_response.text = json.dumps(identity_resp)

        mock_sign_in.return_value = True

        data = {"fragment": "#access_token=abc&token_type=Bearer&random=stuff"}

        resp = self.ajax_post(reverse("sso_landing"), data=data)

        mock_sign_in.assert_called_once()
        args, _ = mock_sign_in.call_args
        self.assertEqual(args[1], identity_resp)

        mock_requests.get.assert_called_once()
        args, kwargs = mock_requests.get.call_args
        url = args[0]
        headers = kwargs["headers"]
        self.assertEqual(
            url, mock_settings.IDENTITY_API_URL, "Identity API URL mismatch"
        )
        self.assertDictEqual(
            headers,
            {"x-api-key": mock_settings.OAUTH_CLIENT_ID, "Authorization": "Bearer abc"},
        )
        self.assertJSONEqual(resp.content, {"error": None, "resp": "/"})

    @patch("meals.views.admin.requests")
    @patch("meals.views.admin.settings")
    @patch("meals.views.admin.sign_in_netid_user")
    def test_identity_api_error(self, mock_sign_in, mock_settings, mock_requests):
        """Tests when IDENTITY_API returns error response"""
        mock_settings.OAUTH_CLIENT_ID = "123"
        mock_settings.IDENTITY_API_URL = "https://fake.oit.duke.edu"
        mock_response = Mock(spec=Response)
        mock_requests.get.return_value = mock_response

        mock_response.status_code = 500
        mock_response.text = json.dumps({"error": "Service temporarily unavailable."})

        with self.assertLogs(admin_logger, level="INFO") as cm:
            self.ajax_post(reverse("sso_landing"), data={
                "fragment": "#access_token=abc&token_type=Bearer"
            })

        self.assertInAny("User token type: Bearer", cm.output)
        self.assertInAny("error from IDENTITY_API", cm.output)

        mock_sign_in.assert_not_called()