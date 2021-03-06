# -*- coding: utf-8 -*-
import pytest
from django.utils import timezone
from nose.tools import *  # noqa

from framework.auth.core import Auth
from osf_tests.factories import AuthUserFactory, ProjectFactory, UserFactory
from scripts import parse_citation_styles
from tests.base import OsfTestCase
from osf.models import OSFUser as User, AbstractNode as Node
from website.citations.utils import datetime_to_csl
from website.util import api_url_for

pytestmark = pytest.mark.django_db

class CitationsUtilsTestCase(OsfTestCase):
    def test_datetime_to_csl(self):
        # Convert a datetime instance to csl's date-variable schema
        now = timezone.now()

        assert_equal(
            datetime_to_csl(now),
            {'date-parts': [[now.year, now.month, now.day]]},
        )


class CitationsNodeTestCase(OsfTestCase):
    def setUp(self):
        super(CitationsNodeTestCase, self).setUp()
        self.node = ProjectFactory()

    def tearDown(self):
        super(CitationsNodeTestCase, self).tearDown()
        Node.remove()
        User.remove()

    def test_csl_single_author(self):
        # Nodes with one contributor generate valid CSL-data
        assert_equal(
            self.node.csl,
            {
                'publisher': 'Open Science Framework',
                'author': [{
                    'given': self.node.creator.given_name,
                    'family': self.node.creator.family_name,
                }],
                'URL': self.node.display_absolute_url,
                'issued': datetime_to_csl(self.node.logs.latest().date),
                'title': self.node.title,
                'type': 'webpage',
                'id': self.node._id,
            },
        )

    def test_csl_multiple_authors(self):
        # Nodes with multiple contributors generate valid CSL-data
        user = UserFactory()
        self.node.add_contributor(user)
        self.node.save()

        assert_equal(
            self.node.csl,
            {
                'publisher': 'Open Science Framework',
                'author': [
                    {
                        'given': self.node.creator.given_name,
                        'family': self.node.creator.family_name,
                    },
                    {
                        'given': user.given_name,
                        'family': user.family_name,
                    }
                ],
                'URL': self.node.display_absolute_url,
                'issued': datetime_to_csl(self.node.logs.latest().date),
                'title': self.node.title,
                'type': 'webpage',
                'id': self.node._id,
            },
        )

    def test_non_visible_contributors_arent_included_in_csl(self):
        node = ProjectFactory()
        visible = UserFactory()
        node.add_contributor(visible, auth=Auth(node.creator))
        invisible = UserFactory()
        node.add_contributor(invisible, auth=Auth(node.creator), visible=False)
        node.save()
        assert_equal(len(node.csl['author']), 2)
        expected_authors = [
            contrib.csl_name for contrib in [node.creator, visible]
        ]

        assert_equal(node.csl['author'], expected_authors)

class CitationsUserTestCase(OsfTestCase):
    def setUp(self):
        super(CitationsUserTestCase, self).setUp()
        self.user = UserFactory()

    def tearDown(self):
        super(CitationsUserTestCase, self).tearDown()
        User.remove()

    def test_user_csl(self):
        # Convert a User instance to csl's name-variable schema
        assert_equal(
            self.user.csl_name,
            {
                'given': self.user.given_name,
                'family': self.user.family_name,
            },
        )


class CitationsViewsTestCase(OsfTestCase):

    @pytest.fixture(autouse=True)
    def _parsed_citation_styles(self):
        # populate the DB with parsed citation styles
        try:
            parse_citation_styles.main()
        except OSError:
            pass

    def test_list_styles(self):
        # Response includes a list of available citation styles
        response = self.app.get(api_url_for('list_citation_styles'))

        assert_true(response.json)

        assert_equal(
            len(
                [
                    style for style in response.json['styles']
                    if style.get('id') == 'bibtex'
                ]
            ),
            1,
        )

    def test_list_styles_filter(self):
        # Response includes a list of available citation styles
        response = self.app.get(api_url_for('list_citation_styles', q='bibtex'))

        assert_true(response.json)

        assert_equal(
            len(response.json['styles']), 1
        )

        assert_equal(
            response.json['styles'][0]['id'], 'bibtex'
        )

    def test_node_citation_view(self):
        node = ProjectFactory()
        user = AuthUserFactory()
        node.add_contributor(user)
        node.save()
        response = self.app.get("/api/v1" + "/project/" + node._id + "/citation/", auto_follow=True, auth=user.auth)
        assert_true(response.json)
