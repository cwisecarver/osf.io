import mock
import csv
import furl
import pytz
import pytest
from datetime import datetime, timedelta

from nose import tools as nt
from django.test import RequestFactory
from django.http import Http404
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission

from tests.base import AdminTestCase
from website import settings
from framework.auth import Auth
from osf.models.user import OSFUser
from osf_tests.factories import (
    UserFactory,
    AuthUserFactory,
    ProjectFactory,
    TagFactory,
    UnconfirmedUserFactory
)
from admin_tests.utilities import setup_view, setup_log_view, setup_form_view

from admin.users import views
from admin.users.forms import WorkshopForm, UserSearchForm
from osf.models.admin_log_entry import AdminLogEntry

pytestmark = pytest.mark.django_db


class TestUserView(AdminTestCase):
    def test_no_guid(self):
        request = RequestFactory().get('/fake_path')
        view = views.UserView()
        view = setup_view(view, request)
        with nt.assert_raises(AttributeError):
            view.get_object()

    def test_load_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = views.UserView()
        view = setup_view(view, request, guid=guid)
        res = view.get_object()
        nt.assert_is_instance(res, dict)

    def test_name_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = views.UserView()
        view = setup_view(view, request, guid=guid)
        temp_object = view.get_object()
        view.object = temp_object
        res = view.get_context_data()
        nt.assert_equal(res[views.UserView.context_object_name], temp_object)

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(reverse('users:user', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            views.UserView.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        view_permission = Permission.objects.get(codename='view_osfuser')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(reverse('users:user', kwargs={'guid': guid}))
        request.user = user

        response = views.UserView.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class TestResetPasswordView(AdminTestCase):
    def setUp(self):
        super(TestResetPasswordView, self).setUp()
        self.user = UserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.plain_view = views.ResetPasswordView
        self.view = setup_view(self.plain_view(), self.request, guid=self.user._id)

    def test_get_initial(self):
        self.view.user = self.user
        self.view.get_initial()
        res = self.view.initial
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['guid'], self.user._id)
        nt.assert_equal(res['emails'], [(r, r) for r in self.user.emails.values_list('address', flat=True)])

    def test_reset_password_context(self):
        self.view.user = self.user
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_in((self.user.emails.first().address, self.user.emails.first().address), self.view.initial['emails'])

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()

        guid = user._id
        request = RequestFactory().get(reverse('users:reset_password', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            views.ResetPasswordView.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('users:reset_password', kwargs={'guid': guid}))
        request.user = user

        response = views.ResetPasswordView.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class TestDisableUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = views.UserDeleteView
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_get_object(self):
        obj = self.view().get_object()
        nt.assert_is_instance(obj, OSFUser)

    def test_get_context(self):
        res = self.view().get_context_data(object=self.user)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.user._id)

    def test_disable_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        count = AdminLogEntry.objects.count()
        self.view().delete(self.request)
        self.user.reload()
        nt.assert_true(self.user.is_disabled)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_reactivate_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        self.view().delete(self.request)
        count = AdminLogEntry.objects.count()
        self.view().delete(self.request)
        self.user.reload()
        nt.assert_false(self.user.is_disabled)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_no_user(self):
        view = setup_view(views.UserDeleteView(), self.request, guid='meh')
        with nt.assert_raises(Http404):
            view.delete(self.request)

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(reverse('users:disable', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('users:disable', kwargs={'guid': guid}))
        request.user = user

        response = self.view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)

class TestDisableSpamUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.public_node = ProjectFactory(creator=self.user, is_public=True)
        self.public_node = ProjectFactory(creator=self.user, is_public=False)
        self.request = RequestFactory().post('/fake_path')
        self.view = views.SpamUserDeleteView
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_get_object(self):
        obj = self.view().get_object()
        nt.assert_is_instance(obj, OSFUser)

    def test_get_context(self):
        res = self.view().get_context_data(object=self.user)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.user._id)

    def test_disable_spam_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        count = AdminLogEntry.objects.count()
        self.view().delete(self.request)
        self.user.reload()
        self.public_node.reload()
        nt.assert_true(self.user.is_disabled)
        nt.assert_false(self.public_node.is_public)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 3)

    def test_no_user(self):
        view = setup_view(self.view(), self.request, guid='meh')
        with nt.assert_raises(Http404):
            view.delete(self.request)

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(reverse('users:spam_disable', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('users:spam_disable', kwargs={'guid': guid}))
        request.user = user

        response = self.view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class SpamUserListMixin(object):
    def setUp(self):

        spam_flagged = TagFactory(name='spam_flagged')
        spam_confirmed = TagFactory(name='spam_confirmed')
        ham_confirmed = TagFactory(name='ham_confirmed')

        self.flagged_user = UserFactory()
        self.flagged_user.tags.add(spam_flagged)
        self.flagged_user.save()

        self.spam_user = UserFactory()
        self.spam_user.tags.add(spam_confirmed)
        self.spam_user.save()

        self.ham_user = UserFactory()
        self.ham_user.tags.add(ham_confirmed)
        self.ham_user.save()

        self.request = RequestFactory().post('/fake_path')

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(self.url)
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.plain_view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        view_permission = Permission.objects.get(codename='view_osfuser')
        spam_permission = Permission.objects.get(codename='view_spam')
        user.user_permissions.add(view_permission)
        user.user_permissions.add(spam_permission)
        user.save()

        request = RequestFactory().get(self.url)
        request.user = user

        response = self.plain_view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)

class TestFlaggedSpamUserList(SpamUserListMixin, AdminTestCase):
    def setUp(self):
        super(TestFlaggedSpamUserList, self).setUp()
        self.plain_view = views.UserFlaggedSpamList
        self.view = setup_log_view(self.plain_view(), self.request)
        self.url = reverse('users:flagged-spam')

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        nt.assert_equal(qs.count(), 1)
        nt.assert_equal(qs[0]._id, self.flagged_user._id)


class TestConfirmedSpamUserList(SpamUserListMixin, AdminTestCase):
    def setUp(self):
        super(TestConfirmedSpamUserList, self).setUp()
        self.plain_view = views.UserKnownSpamList
        self.view = setup_log_view(self.plain_view(), self.request)

        self.url = reverse('users:known-spam')

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        nt.assert_equal(qs.count(), 1)
        nt.assert_equal(qs[0]._id, self.spam_user._id)


class TestConfirmedHamUserList(SpamUserListMixin, AdminTestCase):
    def setUp(self):
        super(TestConfirmedHamUserList, self).setUp()
        self.plain_view = views.UserKnownHamList
        self.view = setup_log_view(self.plain_view(), self.request)

        self.url = reverse('users:known-ham')

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        nt.assert_equal(qs.count(), 1)
        nt.assert_equal(qs[0]._id, self.ham_user._id)


class TestRemove2Factor(AdminTestCase):
    def setUp(self):
        super(TestRemove2Factor, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = views.User2FactorDeleteView
        self.setup_view = setup_log_view(self.view(), self.request, guid=self.user._id)

        self.url = reverse('users:remove2factor', kwargs={'guid': self.user._id})

    @mock.patch('osf.models.user.OSFUser.delete_addon')
    def test_remove_two_factor_get(self, mock_delete_addon):
        self.setup_view.delete(self.request)
        mock_delete_addon.assert_called_with('twofactor')

    def test_integration_delete_two_factor(self):
        user_addon = self.user.get_or_add_addon('twofactor')
        nt.assert_not_equal(user_addon, Node.load(None))
        user_settings = self.user.get_addon('twofactor')
        nt.assert_not_equal(user_settings, Node.load(None))
        count = AdminLogEntry.objects.count()
        self.setup_view.delete(self.request)
        post_addon = self.user.get_addon('twofactor')
        nt.assert_equal(post_addon, Node.load(None))
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_no_user_permissions_raises_error(self):
        guid = self.user._id
        request = RequestFactory().get(self.url)
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        guid = self.user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        self.user.user_permissions.add(change_permission)
        self.user.save()

        request = RequestFactory().get(self.url)
        request.user = self.user

        response = self.view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class TestUserWorkshopFormView(AdminTestCase):

    def setUp(self):
        self.user_1 = AuthUserFactory()
        self.auth_1 = Auth(self.user_1)
        self.view = views.UserWorkshopFormView()
        self.workshop_date = timezone.now()
        self.data = [
            ['none', 'date', 'none', 'none', 'none', 'email', 'none'],
            [Node.load(None), self.workshop_date.strftime('%m/%d/%y'), Node.load(None), Node.load(None), Node.load(None), self.user_1.username, Node.load(None)],
        ]

        self.user_exists_by_name_data = [
            ['number', 'date', 'location', 'topic', 'name', 'email', 'other'],
            [Node.load(None), self.workshop_date.strftime('%m/%d/%y'), Node.load(None), Node.load(None), self.user_1.fullname, 'unknown@example.com', Node.load(None)],
        ]

        self.user_not_found_data = [
            ['none', 'date', 'none', 'none', 'none', 'email', 'none'],
            [Node.load(None), self.workshop_date.strftime('%m/%d/%y'), Node.load(None), Node.load(None), Node.load(None), 'fake@example.com', Node.load(None)],
        ]

        self.mock_data = mock.patch.object(
            csv,
            'reader',
            # parse data into the proper format handling Node.load(None) values as csv reader would
            side_effect=(lambda values: [[item or '' for item in value] for value in values])
        )
        self.mock_data.start()

    def tearDown(self):
        self.mock_data.stop()

    def _create_and_parse_test_file(self, data):
        result_csv = self.view.parse(data)

        return result_csv

    def _create_nodes_and_add_logs(self, first_activity_date, second_activity_date=Node.load(None)):
        node_one = ProjectFactory(creator=self.user_1)
        node_one.date_created = first_activity_date
        node_one.add_log(
            'log_added', params={'project': node_one._id}, auth=self.auth_1, log_date=first_activity_date, save=True
        )

        if second_activity_date:
            node_two = ProjectFactory(creator=self.user_1)
            node_two.date_created = second_activity_date
            node_two.add_log(
                'log_added', params={'project': node_two._id}, auth=self.auth_1, log_date=second_activity_date, save=True
            )

    def test_correct_number_of_columns_added(self):
        added_columns = ['OSF ID', 'Logs Since Workshop', 'Nodes Created Since Workshop', 'Last Log Data']
        result_csv = self._create_and_parse_test_file(self.data)
        nt.assert_equal(len(self.data[0]) + len(added_columns), len(result_csv[0]))

    def test_user_activity_day_of_workshop_only(self):
        self._create_nodes_and_add_logs(first_activity_date=self.workshop_date)

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_activity_before_workshop_only(self):
        activity_date = timezone.now() - timedelta(days=1)
        self._create_nodes_and_add_logs(first_activity_date=activity_date)

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_activity_after_workshop_only(self):
        activity_date = timezone.now() + timedelta(hours=25)
        self._create_nodes_and_add_logs(first_activity_date=activity_date)

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 1)
        nt.assert_equal(user_nodes_created_since_workshop, 1)

    def test_user_activity_day_of_workshop_and_before(self):
        activity_date = timezone.now() - timedelta(days=1)
        self._create_nodes_and_add_logs(
            first_activity_date=self.workshop_date,
            second_activity_date=activity_date
        )

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_activity_day_of_workshop_and_after(self):
        activity_date = timezone.now() + timedelta(hours=25)
        self._create_nodes_and_add_logs(
            first_activity_date=self.workshop_date,
            second_activity_date=activity_date
        )

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 1)
        nt.assert_equal(user_nodes_created_since_workshop, 1)

    def test_user_activity_before_workshop_and_after(self):
        before_activity_date = timezone.now() - timedelta(days=1)
        after_activity_date = timezone.now() + timedelta(hours=25)
        self._create_nodes_and_add_logs(
            first_activity_date=before_activity_date,
            second_activity_date=after_activity_date
        )

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        # One log before workshop, one after, only should show the one after
        nt.assert_equal(user_logs_since_workshop, 1)
        nt.assert_equal(user_nodes_created_since_workshop, 1)

    def test_user_osf_account_not_found(self):
        result_csv = self._create_and_parse_test_file(self.user_not_found_data)
        user_id = result_csv[1][-4]
        last_log_date = result_csv[1][-1]
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_id, '')
        nt.assert_equal(last_log_date, '')
        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_found_by_name(self):
        result_csv = self._create_and_parse_test_file(self.user_exists_by_name_data)
        user_id = result_csv[1][-4]
        last_log_date = result_csv[1][-1]
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_id, self.user_1.id)
        nt.assert_equal(last_log_date, '')
        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_form_valid(self):
        request = RequestFactory().post('/fake_path')
        data = [
            ['none', 'date', 'none', 'none', 'none', 'email', 'none'],
            [Node.load(None), '9/1/16', Node.load(None), Node.load(None), Node.load(None), self.user_1.username, Node.load(None)],
        ]

        uploaded = SimpleUploadedFile('test_name', bytes(csv.reader(data)), content_type='text/csv')

        form = WorkshopForm(data={'document': uploaded})
        form.is_valid()
        form.cleaned_data['document'] = uploaded
        setup_form_view(self.view, request, form)


class TestUserSearchView(AdminTestCase):

    def setUp(self):
        self.user_1 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user_2 = AuthUserFactory(fullname='Jeff Hardy')
        self.user_3 = AuthUserFactory(fullname='Reby Sky')
        self.user_4 = AuthUserFactory(fullname='King Maxel Hardy')

        self.user_2_alternate_email = 'brothernero@delapidatedboat.com'
        self.user_2.emails.create(address=self.user_2_alternate_email)
        self.user_2.save()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.UserFormView()
        self.view = setup_form_view(self.view, self.request, form=UserSearchForm())

    def test_search_user_by_guid(self):
        form_data = {
            'guid': self.user_1.guids.first()._id
        }
        form = UserSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(self.view.success_url, '/users/{}/'.format(self.user_1.guids.first()._id))

    def test_search_user_by_name(self):
        form_data = {
            'name': 'Hardy'
        }
        form = UserSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(self.view.success_url, '/users/search/Hardy/')

    def test_search_user_by_username(self):
        form_data = {
            'email': self.user_1.username
        }
        form = UserSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(self.view.success_url, '/users/{}/'.format(self.user_1.guids.first()._id))

    def test_search_user_by_alternate_email(self):
        form_data = {
            'email': self.user_2_alternate_email
        }
        form = UserSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(self.view.success_url, '/users/{}/'.format(self.user_2.guids.first()._id))

    def test_search_user_list(self):
        view = views.UserSearchList()
        view = setup_view(view, self.request)
        view.kwargs = {'name': 'Hardy'}

        results = view.get_queryset()

        nt.assert_equal(len(results), 3)
        for user in results:
            nt.assert_in('Hardy', user.fullname)

    def test_search_user_list_case_insensitive(self):
        view = views.UserSearchList()
        view = setup_view(view, self.request)
        view.kwargs = {'name': 'hardy'}

        results = view.get_queryset()

        nt.assert_equal(len(results), 3)
        for user in results:
            nt.assert_in('Hardy', user.fullname)


class TestGetLinkView(AdminTestCase):

    def test_get_user_confirmation_link(self):
        user = UnconfirmedUserFactory()
        request = RequestFactory().get('/fake_path')
        view = views.GetUserConfirmationLink()
        view = setup_view(view, request, guid=user._id)

        user_token = user.email_verifications.keys()[0]
        ideal_link_path = '/confirm/{}/{}/'.format(user._id, user_token)
        link = view.get_link(user)
        link_path = str(furl.furl(link).path)

        nt.assert_equal(link_path, ideal_link_path)

    def test_get_user_confirmation_link_with_expired_token(self):
        user = UnconfirmedUserFactory()
        request = RequestFactory().get('/fake_path')
        view = views.GetUserConfirmationLink()
        view = setup_view(view, request, guid=user._id)

        old_user_token = user.email_verifications.keys()[0]
        user.email_verifications[old_user_token]['expiration'] = datetime.utcnow().replace(tzinfo=pytz.utc) - timedelta(hours=24)
        user.save()

        link = view.get_link(user)
        new_user_token = user.email_verifications.keys()[0]

        link_path = str(furl.furl(link).path)
        ideal_link_path = '/confirm/{}/{}/'.format(user._id, new_user_token)

        nt.assert_equal(link_path, ideal_link_path)

    def test_get_password_reset_link(self):
        user = UnconfirmedUserFactory()
        request = RequestFactory().get('/fake_path')
        view = views.GetPasswordResetLink()
        view = setup_view(view, request, guid=user._id)

        link = view.get_link(user)

        user_token = user.verification_key_v2.get('token')
        nt.assert_is_not_none(user_token)

        ideal_link_path = '/resetpassword/{}/{}'.format(user._id, user_token)
        link_path = str(furl.furl(link).path)

        nt.assert_equal(link_path, ideal_link_path)

    def test_get_unclaimed_node_links(self):
        project = ProjectFactory()
        unregistered_contributor = project.add_unregistered_contributor(fullname='Brother Nero', email='matt@hardyboyz.biz', auth=Auth(project.creator))
        project.save()

        request = RequestFactory().get('/fake_path')
        view = views.GetUserClaimLinks()
        view = setup_view(view, request, guid=unregistered_contributor._id)

        links = view.get_claim_links(unregistered_contributor)
        unclaimed_records = unregistered_contributor.unclaimed_records

        nt.assert_equal(len(links), 1)
        nt.assert_equal(len(links), len(unclaimed_records.keys()))
        link = links[0]

        nt.assert_in(project._id, link)
        nt.assert_in(unregistered_contributor.unclaimed_records[project._id]['token'], link)


class TestUserReindex(AdminTestCase):
    def setUp(self):
        super(TestUserReindex, self).setUp()
        self.request = RequestFactory().post('/fake_path')

        self.user = AuthUserFactory()

    @mock.patch('website.search.search.update_user')
    def test_reindex_user_elastic(self, mock_reindex_elastic):
        count = AdminLogEntry.objects.count()
        view = views.UserReindexElastic()
        view = setup_log_view(view, self.request, guid=self.user._id)
        view.delete(self.request)

        nt.assert_true(mock_reindex_elastic.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)
