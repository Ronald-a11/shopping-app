from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from supermarket.models import ContactMessage, MessageReply

# Production-only settings get in the way of the test client: the HTTPS
# redirect turns every request into a 301, and the manifest static storage
# needs collectstatic to have run.
TEST_SETTINGS = {
    'SECURE_SSL_REDIRECT': False,
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
    'PASSWORD_HASHERS': ['django.contrib.auth.hashers.MD5PasswordHasher'],
}

CONTACT_FORM = {
    'name': 'Tendai Moyo',
    'phone_number': '0771234567',
    'gender': 'prefer_not_to_say',
    'age_group': '26_35',
    'message_type': 'inquiry',
    'subject': 'Opening hours',
    'message': 'Are you open on Sundays?',
}


@override_settings(**TEST_SETTINGS)
class ContactMessageRepliesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user('staff', password='pw', is_staff=True, first_name='Ronald')
        cls.customer = User.objects.create_user('tendai', password='pw', first_name='Tendai')
        cls.other_customer = User.objects.create_user('rudo', password='pw')
        cls.message = ContactMessage.objects.create(
            user=cls.customer, name='Tendai Moyo', phone_number='0771234567',
            message_type='complaint', subject='Late delivery', message='My order came late.',
        )
        cls.anonymous_message = ContactMessage.objects.create(
            name='Rudo Dube', phone_number='0771111111',
            subject='Delivery area', message='Do you deliver to Chiredzi?',
        )

    def staff_reply(self, message, **data):
        self.client.force_login(self.staff)
        return self.client.post(reverse('reply_to_message', args=[message.id]), data)

    # Sending a message ---------------------------------------------------

    def test_message_from_logged_in_customer_is_linked_to_their_account(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('contact'), CONTACT_FORM)

        self.assertRedirects(response, reverse('my_messages'))
        self.assertEqual(ContactMessage.objects.get(subject='Opening hours').user, self.customer)

    def test_message_from_visitor_has_no_account(self):
        response = self.client.post(reverse('contact'), CONTACT_FORM)

        self.assertRedirects(response, reverse('contact'))
        self.assertIsNone(ContactMessage.objects.get(subject='Opening hours').user)

    # Staff replies ---------------------------------------------------------

    def test_staff_reply_is_saved_and_marks_the_message_replied(self):
        response = self.staff_reply(self.message, body='Sorry about that, we will call you today.')

        reply = MessageReply.objects.get()
        self.assertRedirects(
            response, f"{reverse('message_detail', args=[self.message.id])}#reply-{reply.id}",
            fetch_redirect_response=False,
        )
        self.assertTrue(reply.from_staff)
        self.assertEqual(reply.author, self.staff)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'replied')
        self.assertTrue(self.message.is_read)

    def test_staff_can_resolve_while_replying(self):
        self.staff_reply(self.message, body='Refund issued.', mark_resolved='on')

        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'resolved')

    def test_blank_reply_is_rejected_with_an_error(self):
        response = self.staff_reply(self.message, body='   ')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(MessageReply.objects.exists())
        self.assertIn('body', response.context['reply_form'].errors)

    def test_customers_cannot_post_staff_replies(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('reply_to_message', args=[self.message.id]), {'body': 'Hi'})

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        self.assertFalse(MessageReply.objects.exists())

    def test_toggle_resolved_closes_and_reopens(self):
        self.client.force_login(self.staff)
        url = reverse('toggle_resolved', args=[self.message.id])

        self.client.post(url)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'resolved')

        # Nobody has replied yet, so reopening puts it back in the queue.
        self.client.post(url)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'open')

    def test_reply_to_visitor_offers_whatsapp_with_the_reply_filled_in(self):
        self.staff_reply(self.anonymous_message, body='Yes, we deliver there.')

        response = self.client.get(reverse('message_detail', args=[self.anonymous_message.id]))
        self.assertContains(response, 'https://wa.me/263771111111?text=Hi%20Rudo')
        self.assertContains(response, 'sms:+263771111111?body=')

    def test_awaiting_reply_filter_lists_only_open_messages(self):
        self.staff_reply(self.message, body='Handled.')

        response = self.client.get(reverse('dashboard_messages'), {'filter': 'open'})
        listed = list(response.context['contact_messages'].object_list)
        self.assertEqual(listed, [self.anonymous_message])
        self.assertEqual(response.context['open_count'], 1)

    # The customer's side ---------------------------------------------------

    def test_customer_sees_the_reply_and_it_is_marked_read(self):
        reply = MessageReply.objects.create(message=self.message, author=self.staff, body='We are on it.')
        self.client.force_login(self.customer)

        contact_page = self.client.get(reverse('contact'))
        self.assertEqual(contact_page.context['unread_replies'], 1)

        response = self.client.get(reverse('my_messages'))
        self.assertContains(response, 'We are on it.')
        self.assertIn(reply.id, response.context['new_reply_ids'])
        reply.refresh_from_db()
        self.assertTrue(reply.read_by_customer)
        self.assertEqual(response.context['unread_replies'], 0)

    def test_customer_does_not_see_other_peoples_messages(self):
        self.client.force_login(self.other_customer)
        response = self.client.get(reverse('my_messages'))

        self.assertNotContains(response, 'Late delivery')
        self.assertNotContains(response, 'Delivery area')

    def test_customer_follow_up_reopens_the_conversation(self):
        self.message.status = 'replied'
        self.message.is_read = True
        self.message.save()
        self.client.force_login(self.customer)

        response = self.client.post(reverse('customer_reply', args=[self.message.id]), {'body': 'Still waiting.'})

        self.assertRedirects(response, f"{reverse('my_messages')}#message-{self.message.id}", fetch_redirect_response=False)
        reply = MessageReply.objects.get()
        self.assertFalse(reply.from_staff)
        self.assertEqual(reply.author, self.customer)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, 'open')
        self.assertFalse(self.message.is_read)

    def test_customer_cannot_reply_to_someone_elses_message(self):
        self.client.force_login(self.other_customer)
        response = self.client.post(reverse('customer_reply', args=[self.message.id]), {'body': 'Hi'})

        self.assertEqual(response.status_code, 404)
        self.assertFalse(MessageReply.objects.exists())
