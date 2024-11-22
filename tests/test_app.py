import unittest
from app import app
import unittest
from flask import Flask, session
from app import app  # Replace with the actual file name of your Flask app
from unittest.mock import patch, MagicMock

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        # Create a test client
        self.app = app.test_client()
        self.app.testing = True

    # Test GET /api/submissions
    def test_get_submissions(self):
        response = self.app.get('/api/submissions?year=2024&month=11')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, dict)

    # Test /admin_dashboard requires login and role
    def test_admin_dashboard(self):
        with self.app.session_transaction() as session:
            session['role'] = 'admin'
            session['name'] = 'Admin'
            session['surname'] = 'User'
        response = self.app.get('/admin_dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Dashboard', response.data)

    # Test /add_user invalid email
    def test_add_user_invalid_email(self):
        response = self.app.post('/add_user', data={
            'name': 'Test',
            'surname': 'User',
            'email': 'invalid@gmail.com',
            'password': '123456',
            'role': 'lecturer',
            'qualification': 'PhD'
        })
        self.assertIn(b'Email must end with @ump.ac.za', response.data)

    # Test /view_event
    def test_view_event(self):
        response = self.app.get('/view_event/test_module_id')
        self.assertEqual(response.status_code, 200)

    # Test /forgot_pass POST
    def test_forgot_password(self):
        response = self.app.post('/forgot_pass', data={'email': 'user@ump.ac.za'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'password reset', response.data.lower())

    # Test /process_submission
    def test_process_submission(self):
        with self.app.session_transaction() as session:
            session['user_id'] = 'test_user'
        response = self.app.post('/process_submission/test_module/test_event', data={
            'document': (io.BytesIO(b'Test file content'), 'test_file.pdf')
        })
        self.assertEqual(response.status_code, 302)  # Redirect on success

    # Test /delete_event
    def test_delete_event(self):
        response = self.app.post('/delete_event/test_module/test_event')
        self.assertEqual(response.status_code, 302)

    # Test /profile_lecture
    def test_profile_lecture(self):
        with self.app.session_transaction() as session:
            session['role'] = 'lecturer'
            session['name'] = 'Lecturer'
            session['surname'] = 'User'
            session['user_id'] = 'test_user_id'
        response = self.app.get('/profile_lecture')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Lecturer Profile', response.data)





class SignInRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.verify_user_credentials')
    @patch('app.auth.get_user_by_email')
    @patch('app.db.collection')
    def test_valid_sign_in(self, mock_db, mock_get_user_by_email, mock_verify_user_credentials):
        mock_verify_user_credentials.return_value = {}
        mock_user = MagicMock(uid='12345')
        mock_get_user_by_email.return_value = mock_user
        mock_user_doc = MagicMock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            'name': 'John',
            'surname': 'Doe',
            'role': 'admin'
        }
        mock_db.return_value.document.return_value.get.return_value = mock_user_doc

        response = self.app.post('/sign_in', data={
            'email': '123456789@ump.ac.za',
            'password': 'Password@123'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('admin_dashboard', response.location)

    def test_invalid_email_format(self):
        response = self.app.post('/sign_in', data={
            'email': 'invalid_email',
            'password': 'Password@123'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email format', response.data)

    def test_weak_password(self):
        response = self.app.post('/sign_in', data={
            'email': '123456789@ump.ac.za',
            'password': 'weakpass'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password must be at least 8 characters', response.data)

    @patch('app.verify_user_credentials')
    def test_invalid_credentials(self, mock_verify_user_credentials):
        mock_verify_user_credentials.return_value = {'error': {'message': 'Invalid credentials'}}
        
        response = self.app.post('/sign_in', data={
            'email': '123456789@ump.ac.za',
            'password': 'Password@123'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid credentials', response.data)

    @patch('app.auth.get_user_by_email')
    def test_user_role_not_found(self, mock_get_user_by_email):
        mock_user = MagicMock(uid='12345')
        mock_get_user_by_email.return_value = mock_user

        response = self.app.post('/sign_in', data={
            'email': '123456789@ump.ac.za',
            'password': 'Password@123'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'User role not found', response.data)


 






















if __name__ == '__main__':
    unittest.main()

